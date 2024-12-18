from pygame.math import Vector2
import math
import pygame

class PhysicsObject:
    def __init__(self, mass=1, pos=(0,0), vel=(0,0), momi=math.inf, angle=0, avel=0, torque=0):
        self.mass = mass
        self.pos = Vector2(pos) # need to make pos a Vector2, and a new one
        self.momi = momi
        self.angle = angle
        self.avel = avel
        self.torque = torque
        self.vel = Vector2(vel)
        self.force = Vector2(0,0)

    def clear_force(self):
        self.force = Vector2(0,0)
        self.torque = 0
        
    def add_force(self, force):
        self.force += force

    def apply_gravity(self, vel):
        self.vel -= (0,-8)

    def impulse(self, impulse, point=None):
        self.vel += Vector2(impulse)/self.mass
        if point is not None:
            s = point - self.pos
            self.avel += math.degrees(s.cross(impulse)/self.momi)
    
    def update(self, dt):
        # update velocity using the current force
        self.vel += self.force/self.mass * dt
        # update position using the newly updated velocity
        self.pos += self.vel * dt
        self.avel += self.torque/self.momi * dt
        self.angle += self.avel * dt
    
    def set(self, pos=None, angle=None):
        if pos is not None:
            self.pos = Vector2(pos)
        if angle is not None:
            self.angle = angle

class Circle(PhysicsObject):
    def __init__(self, radius, color=(255,255,255), width=0, fixed=False, **kwargs):
        self.radius = radius
        self.color = color
        self.width = width
        self.fixed = fixed
        self.contact_type = "Circle"
        super().__init__(**kwargs)
   
    def draw(self, surface):
        pygame.draw.circle(surface, self.color, self.pos, self.radius, self.width)
    
    def Isclick(self, point):
        return (self.pos - Vector2(point)).length() <= self.radius
    
class Wall(PhysicsObject):
    def __init__(self, point1, point2, color=(255, 255, 255), width=1):
        self.point1 = Vector2(point1)
        self.point2 = Vector2(point2)
        self.color = color
        self.width = width
        direction = self.point2 - self.point1
        self.normal = Vector2(-direction.y, direction.x).normalize()
        self.contact_type = "Wall"
        super().__init__(mass=math.inf, pos=self.point1)
    
    def draw(self, surface):
        pygame.draw.line(surface, self.color, self.point1, self.point2, self.width)

class UniformCircle(Circle):
    def __init__(self, radius=100, density=None, mass=None, **kwargs):
        if mass is not None and density is not None:
            raise("Cannot specify both mass and density.")
        if mass is None and density is None:
            mass = 1 # if neither mass or density is specified, default to mass = 1

        # if mass is not defined, calculate it based on density*area               
        if mass is None:
            mass = density * math.pi * radius**2
            pass
        
        # calculate moment of inertia
        momi = 0.5 * radius**2

        super().__init__(mass=mass, momi=momi, radius=radius, **kwargs)  


class Polygon(PhysicsObject):
    def __init__(self, local_points=[], color=(255,255,255), width=0, normals_length=0, **kwargs):
        self.local_points = [Vector2(local_point) for local_point in local_points]
        self.local_normals = []
        for i in range(len(self.local_points)):
            self.local_normals.append((self.local_points[i] - self.local_points[i-1]).normalize().rotate(90))
        self.check_convex()
        self.color = color
        self.width = width
        self.normals_length = normals_length
        self.contact_type = "Polygon"
        super().__init__(**kwargs)
        self.update(0)

    def check_convex(self):
        if len(self.local_points) > 2:
            n = len(self.local_points)
            convex = True
            for i in range(n):
                d = [(self.local_points[j%n] - self.local_points[i]).dot(self.local_normals[i])
                     for j in range(i+1, i+n-1)]
                #print(min(d), max(d))
                if max(d) <= 0:
                    pass
                elif min(d) >= 0:
                    self.local_normals[i] *= -1
                else:
                    convex = False
            if not convex:
                print("WARNING! Non-convex polygon defined. Collisions will be inncorrect.")


    def update(self, dt):
        super().update(dt)
        self.points = [local_point.rotate(self.angle) + self.pos for local_point in self.local_points]
        self.normals = [local_normal.rotate(self.angle) for local_normal in self.local_normals]

    def draw(self, window):
        pygame.draw.polygon(window, self.color, self.points, self.width)
        if self.normals_length > 0:
            for point, normal in zip(self.points, self.normals):
                pygame.draw.line(window, self.color, point, point + normal*self.normals_length)
    
    def set(self, pos=None, angle=None):
        super().set(pos=pos, angle=angle)
        self.update(0)

class UniformPolygon(Polygon):
    def __init__(self, density=None, local_points=[], pos=[0,0], angle=0, shift=True, mass=None, **kwargs):
        if mass is not None and density is not None:
            raise("Cannot specify both mass and density.")
        if mass is None and density is None:
            mass = 1 # if neither mass or density is specified, default to mass = 1
            density = 1 # it must be defined, but its value doesn't matter when mass is specified
        
        # Calculate mass, moment of inertia, and center of mass based on density
        # by looping over all "triangles" of the polygon
        total_mass = 0
        total_momi = 0
        center_of_mass_numerator = Vector2(0,0)
        for i in range(len(local_points)):
            # triangle mass
            s0 = Vector2(local_points[i])
            s1 = Vector2(local_points[i-1])
            # triangle moment of inertia
            tri_area = 0.5 * s0.cross(s1)
            tri_area = 0.5 * Vector2.cross(s0, s1) # another way to write it
            # triangle center of mass
            delta_mass = density * tri_area
            # add to total mass
            total_mass += delta_mass
            # add to total moment of inertia
            delta_in = (delta_mass / 6) * (s0 * s0 + s1 * s1 + s0 * s1)
            total_momi += delta_in
            # add to center of mass numerator
            pass
                    
        # calculate total center of mass by dividing numerator by denominator (total mass)
        com = center_of_mass_numerator / total_mass

        delta_com = (s0 + s1) / 3
        # if mass is specified, then scale total_mass and total_momi
        if mass is not None:
            total_momi *= mass/total_mass
            total_mass = mass

        # Usually we shift local_points origin to center of mass
        if shift:
            com = Vector2(10,5)
            # Shift all local_points by subtracting com
            for i in range(len(local_points)):
                local_points[i] -= com
            # Shift pos by adding com
            pos = pos + com
            # Use parallel axis theorem to correct the moment of inertia (total_momi)
            total_momi_off_center = total_momi
            total_momi = total_momi_off_center - total_mass * com.magnitude()**2
            pass

        # Then call super().__init__() with those correct values
        super().__init__(mass=abs(total_mass), momi=abs(total_momi), local_points=local_points, pos=pos, angle=angle, **kwargs)

# Test UniformPolygon
shape = UniformPolygon(density=0.01, local_points=[[0,0],[20,0],[20,10],[0,10]])
print(f"Check mass: {shape.mass} = {0.01*10*20}")  # check mass
print(f"Check momi: {shape.momi} = {shape.mass/12*(10**2+20**2)}")  # check moment of inertia
print([shape.local_points]) # check if rectangle is centered (checks center of mass)
print([[-10,-5],[10,-5],[10,5],[-10,5]])