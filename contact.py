import pygame
from pygame.math import Vector2
import math
import random
from physics_objects import Circle, Wall, Polygon
clock = pygame.time.Clock()
fps = 60
dt = 1/fps
# Returns a new contact object of the correct subtype
# This function has been done for you.
def generate(a, b, **kwargs):
    # Check if a's type comes later than b's alphabetically.
    # We will label our collision types in alphabetical order, 
    # so the lower one needs to go first.
    if b.contact_type < a.contact_type:
        a, b = b, a
    # This calls the class of the appropriate name based on the two contact types.
    return globals()[f"{a.contact_type}_{b.contact_type}"](a, b, **kwargs)
    
# Generic contact class, to be overridden by specific scenarios
class Contact():
    def __init__(self, a, b, resolve=False, **kwargs):
        self.a = a
        self.b = b
        self.kwargs = kwargs
        self.overlap = 0
        self.update()
        self.bool = self.overlap > 0
        if resolve:
            self.bool = self.resolve(update=False)

    def __bool__(self):
        return self.bool 

    def update(self):  # virtual function
        self.overlap = 0
        self.normal = Vector2(0, 0), 

    def resolve(self, restitution=None, rebound=None, friction=None, update=True):
        if update:
            self.update()
        restitution = restitution if restitution is not None else self.kwargs.get("restitution", 0)
        rebound = rebound if rebound is not None else self.kwargs.get("rebound", 0)
        friction = friction if friction is not None else self.kwargs.get("friction", 0)
        # ^ priority for restitution is: 1 argument in resolve, 2 argument in generate, 3 default value = 1 (elastic)
        # resolve overlap
        if self.overlap <= 0:
            return False

        # calculate new reduced mass that includes the extra terms for rotation
        # m = 1/(1/self.a.mass + 1/self.b.mass) # reduced mass

        # resolve velocity
        # return True if impulses need to be applied, return False otherwise
        sa = self.point() - self.a.pos
        # sa * Jn = sa.rortate(90) * Jn

        vpa = self.a.vel + math.radians(self.a.avel) * sa.rotate(90)
        sb = self.point() - self.b.pos
        vpb = self.b.vel + math.radians(self.b.avel) * sb.rotate(90)
        v = vpa - vpb
        m = 1 /( (1/self.a.mass) + (1/self.b.mass) + ((sa.cross(self.normal))**2 / self.a.momi) + ((sb.cross(self.normal))**2 / self.b.momi))
        self.a.set(pos=self.a.pos + m/self.a.mass*self.overlap*self.normal)
        self.b.set(pos=self.b.pos - m/self.b.mass*self.overlap*self.normal)

        #v = self.a.vel - self.b.vel
        vdotn = v * self.normal
        if vdotn >= 0:
            return False
        # define tangent (t)
        tangent = self.normal.rotate(90)
        # calculate v dot t
        vdott = v * tangent
        # flip tangent if v dot t is positive
        if vdott > 0:
            tangent *= -1
        # calculate Jf to stop all sliding
            vdott = v * tangent
        Jf = -m * vdott
        #check if Jf is too strong
        Jn = -(1 + restitution) * m * vdotn
        Jfmax = friction * Jn
        if Jf <= Jfmax : # not too strong
        # if not too strong correct for creep
            shift = self.overlap * vdott/vdotn
            self.a.pos += m/self.a.mass * shift * tangent
            self.b.pos -= m/self.b.mass * shift * tangent
        else: 
        # if too strong, set it to the maximum value
            Jf = Jfmax

        impulse = Jn * self.normal + Jf * tangent # note the added second term
        
        self.a.impulse(impulse, self.point())
        self.b.impulse(-impulse, self.point())
        return True
    

# Contact class for two circles
class Circle_Circle(Contact):
    def update(self):  # compute the appropriate values
        r = self.a.pos - self.b.pos
        self.overlap = self.a.radius + self.b.radius - r.magnitude()
        self.normal = r.normalize()
        if r.magnitude() != 0:
            self.normal = r.normalize()
        else:
            self.normal = Vector2(1, 0).rotate(random.uniform(0,360))

    def point(self):
        return self.a.pos - self.a.radius * self.normal


# Contact class for Circle and a Wall
# Circle is before Wall because it comes before it in the alphabet
class Circle_Polygon(Contact):
    def __init__(self, a, b, **kwargs):
        self.circle = a
        self.polygon = b
        super().__init__(a, b, **kwargs)

    def update(self):  # compute the appropriate values
        self.overlap = math.inf
        for i, (wall_pos, wall_normal) in enumerate (zip(self.polygon.points, self.polygon.normals)):
            r = self.circle.pos - wall_pos
            overlap = self.circle.radius - r * wall_normal

            if overlap < self.overlap:
                self.overlap = overlap
                self.normal = wall_normal

                index = i
        

        if 0 < self.overlap < self.circle.radius:
            r = self.circle.pos - self.polygon.points[index]

            s = self.polygon.points[index - 1] - self.polygon.points[index]

            if r * s < 0:
                self.normal = r.normalize()
                self.overlap = self.circle.radius - r.magnitude()
                
            
            
            r = self.circle.pos - self.polygon.points[index - 1]
            s = self.polygon.points[index] - self.polygon.points[index - 1]
            if r * s < 0:
                self.normal = r.normalize()
                self.overlap = self.circle.radius - r.magnitude()
            
    def point(self):
        return self.circle.pos - self.circle.radius * self.normal
class Polygon_Wall(Contact):
    def __init__(self, a, b, **kwargs):
        self.polygon = a
        self.wall = b
        super().__init__(a, b, **kwargs)

    def update(self):  # compute the appropriate values
        self.overlap = -math.inf
        # loop over all polygon points
        for i, point in enumerate(self.polygon.points):
        # find the overlap of that point with the wall
            r = point - self.wall.pos
            overlap = 0 - r.dot(self.wall.normal)
            # if the overlap is greater than self.overlap
            # set self.overlap, self.normal, and self.index
            if overlap > self.overlap:
                self.overlap = overlap
                self.normal = self.wall.normal
                self.index = i

    def point(self):
        return self.polygon.points[self.index]
# Empty class for Wall - Wall collisions
# The intersection of two infinite walls is not interesting, so skip them
class Polygon_Polygon(Contact):
    def update(self):
        self.a:Polygon
        self.b:Polygon
        self.overlap = math.inf # holds the least overlap
        #Case 1: a is polygon, b is list of walls
        polygon = self.a
        for (wall_pos, wall_normal) in zip(self.b.points, self.b.normals):
            # find the overlap of the polygon with the wall
            wall_overlap = -math.inf
            # loop over all polygon points
            for i, point in enumerate(polygon.points):
            # find the overlap of that point with the wall
                r = point - wall_pos
                overlap = 0 - r * wall_normal
                # if the overlap is greater than self.overlap
                # set self.overlap, self.normal, and self.index
                if overlap > wall_overlap:
                    wall_overlap = overlap
                    wall_index = i
            # see if wall_overlap is less than self.overlap
            if wall_overlap < self.overlap:
                self.overlap = wall_overlap
                self.normal = wall_normal
                self.index = wall_index
                self.polygon = polygon # the polygon that the most overlap point belongs to

        #Case 2: b is polygon, a is list of walls
        polygon = self.b
        for (wall_pos, wall_normal) in zip(self.a.points, self.a.normals):
            # find the overlap of the polygon with the wall
            wall_overlap = -math.inf
            # loop over all polygon points
            for i, point in enumerate(polygon.points):
            # find the overlap of that point with the wall
                r = point - wall_pos
                overlap = 0 - r * wall_normal
                # if the overlap is greater than self.overlap
                # set self.overlap, self.normal, and self.index
                if overlap > wall_overlap:
                    wall_overlap = overlap
                    wall_index = i
            # see if wall_overlap is less than self.overlap
            if wall_overlap < self.overlap:
                self.overlap = wall_overlap
                self.normal = -wall_normal
                self.index = wall_index
                self.polygon = polygon # the polygon that the most overlap point belongs to

    def point(self):
        return self.polygon.points[self.index]
class Wall_Wall(Contact):
    pass

