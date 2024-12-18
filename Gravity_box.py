import pygame
from pygame.locals import *
from pygame.math import Vector2, Vector3
import random
import pytmx
import math
from pygame import Color
from time import time

from physics_objects import *
import physics_objects
import itertools
import contact

# initialize pygame and open window
pygame.init()
width, height = 600, 600
window = pygame.display.set_mode([width, height])
rect = pygame.Rect(0, 500, 800, 150)
green = (0, 255, 0)
font = pygame.font.SysFont(None, 34)


# timing
start_ticks = pygame.time.get_ticks()
seconds_passed = 0
max_jump = 2
charge_time = 0
Is_charging = False
touch_goal = False
fps = 60
dt = 1/fps
clock = pygame.time.Clock()
bombs_used = 0

# Objects
# Walls for ground and invisible boundaries: left, right, and top
# lazer
lazer = []
explosions = []
# bombs
bombs = []
# This class implements properties you want to have in all objects
class CustomObject:
    def __init__(self, mass=math.inf, restitution=0.2, rebound = 0, score = 0, resolve=True, pinball_type="", thickness=0, **kwargs):
        self.restitution = restitution
        self.rebound = rebound
        self.score = score
        self.resolve = resolve
        self.pinball_type = pinball_type
        super().__init__(mass=mass, width=thickness, **kwargs)  # default is now infinite mass

# These class definitions call CustomObject first in inheritance.
# They extend the definitions form physics_objects.py.
class Polygon(CustomObject, physics_objects.Polygon): pass
class Circle(CustomObject, physics_objects.Circle): pass
class Wall(CustomObject, physics_objects.Wall): pass
class Explosion(Circle):
    def __init__(self, max_radius, expansion_speed, **kwargs):
        self.max_radius = max_radius
        self.expansion_speed = expansion_speed
        super().__init__(**kwargs)
    
    def update(self, dt):
        super().update(dt)
        self.radius += self.expansion_speed * dt
        if self.radius > self.max_radius:
            self.expansion_speed = 0
            self.radius = self.max_radius

    
# Functions
# Helper function to parse hex color data
def parse_color(c):
    a = int(c[1:3], 16)
    r = int(c[3:5], 16)
    g = int(c[5:7], 16)
    b = int(c[7:9], 16)
    return r,g,b,a

# Parse a pytmx object into a physics object
def parse_object(o):
    # Additional properties stored in kwargs
    print(vars(o))
    kwargs = dict()
    for key in o.properties:
        value = o.properties[key]
        if isinstance(value, str):
            # color
            if value[0] == "#":
                kwargs[key] = parse_color(value)
            # list
            elif "," in value:
                alist = value.split(",")
                for i, x in enumerate(alist):
                    try:
                        if float(x) == int(x):
                            alist[i] = int(x)
                        else:
                            alist[i] = float(x)
                    except:
                        pass
                kwargs[key] = alist
            # string
            else: 
                kwargs[key] = value
        else: # int, float, bool
            kwargs[key] = value
    
    # Polygon
    if hasattr(o, "points"):  
        pos = o.points[0]
        points = [Vector2(p.x - pos.x, p.y - pos.y) for p in o.points]
        # handle pivot point that points to a point object in Tiled
        if "pivot" in kwargs:
            p = tmxdata.get_object_by_id(kwargs["pivot"])
            pivot = Vector2(p.x - pos.x, p.y - pos.y)
            del kwargs["pivot"]
        else: 
            pivot = Vector2(0,0)
        shape = Polygon(pos=pos, local_points=points, angle=o.rotation, **kwargs)
        if pivot:
            for p in shape.local_points:
                p -= pivot.rotate(-shape.angle)
            shape.pos += pivot
            shape.update(0)
        return shape
        
    
    # Circle (squares are interpreted as circles)
    elif o.width == o.height:  
        center = (o.x + o.width/2, o.y + o.height/2)
        return Circle(pos=center, radius=o.width/2, **kwargs)
    
    # Rectangle (non-circular ellipses are interpreted as rectangles)
    else:
        points = [(0,0), (o.width,0), (o.width, o.height), (0, o.height)]
        pos = Vector2(o.x, o.y)
        # handle pivot point that points to a point object in Tiled
        if "pivot" in kwargs:
            p = tmxdata.get_object_by_id(kwargs["pivot"])
            pivot = Vector2(p.x - pos.x, p.y - pos.y)
            del kwargs["pivot"]
        else: 
            pivot = Vector2(0,0)
        if "Color" in kwargs:
            print(pos)
        shape = Polygon(pos=pos, local_points=points, angle=o.rotation, **kwargs)
        if pivot:
            for p in shape.local_points:
                p -= pivot.rotate(-shape.angle)
            shape.pos += pivot
            shape.update(0)
        return shape

# Load data from tmx file    
tmxdata = pytmx.load_pygame("Level_Test.tmx")

# Parse data into objects
objects = [parse_object(o) for o in tmxdata.objects]
objects = [o for o in objects if o is not None]
# print(len(objects))

# player
for o in objects:
    if o.pinball_type == "player":
        player = o
player.mass = 1
for i in range(len(player.local_points)):
    player.local_points[i] -= Vector2(45,45)/2
player.pos += Vector2(45,45)/2

# goal
for o in objects:
    if o.pinball_type == "goal":
        goalBox = o
# OBJECTS
# walls
# bumpers
# bonus zones
# paddles
# plunger

# def spawn_bomb(): # spawns a bomb
#     Circle(pos = ((random.randint(0,800)), (random.randint(0,500))), mass=1, vel=(0,10))

def get_pause():
    global paused
    paused = not paused

# Set up lives and score

game_over = False
running = True
paused = False
while running:
    # update the display
    pygame.display.update()
    clock.tick(fps)
    window.fill([0,0,0])

    # EVENT loop
    while event := pygame.event.poll():
        if (event.type == pygame.QUIT 
            or (event.type == pygame.KEYDOWN
                and event.key == pygame.K_ESCAPE)):
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                bombs_used += 1
                mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
                lazer_direction = mouse_pos - player.pos
                if lazer_direction.length() != 0:
                    lazer_direction = lazer_direction.normalize()
                
                lazer_speed = 300
                lazer_vel = lazer_direction * lazer_speed
                
                new_lazer = UniformCircle(pos=player.pos, density=500, vel=lazer_vel, radius=5, color=Color('yellow'))
                lazer.append(new_lazer)

    if not paused:
        # keep shooter on screen
        
        # collisions between bullets and polygons and polygons with each other

        # check bullets hitting ground or going off screen
        
        # check polygons hitting ground or going off screen or hitting shooter
        
        # check bombs hitting ground or going off screen or hitting shooter
        
        # Stages and scoring

    # DRAW & CLEAR
    # Add forces
        for o in objects:
            o.clear_force()
    
        player.add_force((0,300))
    # draw objects
        center_y = height / 2
        shift_y = center_y - player.pos.y
        y = player.pos.y
        
        for o in objects:
            if o.pinball_type == "goal":
                resolve = False
                b = contact.generate(player, o, resolve=resolve, restitution=o.restitution, rebound=o.rebound, friction=0.5)
                if b:
                    touch_goal = True
            else:
                resolve = True
                b = contact.generate(player, o, resolve=resolve, restitution=o.restitution, rebound=o.rebound, friction=0.5)


        for e in reversed(explosions):
            e.update(dt)
            e.draw(window)
            if e.radius == e.max_radius:
                explosions.remove(e)
            for p in explosions:
                h = contact.generate(player, p, resolve=False, restitution=player.restitution, rebound=player.rebound, friction=0.5)
                if h:
                    player.add_force(2800*(player.pos-p.pos).normalize())
                #     charge_time += dt
                #     charge_time = min(charge_time, max_jump)
                #     Is_charging = True
                # else:
                #     Is_charging = False
                # if Is_charging == False and charge_time > 0 or charge_time == max_jump:
                #     print("here")
                #     h = contact.generate(player, p, resolve=player.resolve, restitution=player.restitution, rebound=math.sqrt(charge_time * 940000), friction=0.5)
        
        for o in objects:
            o.pos.y += shift_y
            o.update(0)
            o.draw(window)
    
    player.update(dt)
    for lazers in reversed(lazer):
        lazers.apply_gravity(lazer_vel)
        lazers.update(dt)
        lazers.draw(window)
        for o in objects:
            if o is not player:
                c = contact.generate(lazers, o, resolve=o.resolve, restitution=o.restitution, rebound=o.rebound, friction=0.5)
                if c:
                    lazer.remove(lazers) # If c is not Player?
                    #lazers = Circle(radius=5, color=Color('white'), fixed=False)
                    explosions.append(Explosion(pos=lazers.pos, radius=5, mass=1, color=Color('white'), thickness=5,  max_radius=50, expansion_speed=200))
                    break
    
                    


       

    # draw reserve shooters
    
    # display running score in the corners
    if touch_goal:
        text = font.render(f"Win", True, (255, 255, 255))
        window.blit(text, (window.get_width()/10, window.get_height()/1.5))
    if touch_goal:
        text = font.render(f"Total Bombs: {bombs_used}", True, (255, 255, 255))
        window.blit(text, (window.get_width()/10, window.get_height()/1.25))
    else:
        text = font.render(f"Bombs: {bombs_used}", True, (255, 255, 255))
        window.blit(text, (window.get_width()/10, window.get_height()/1.25))
    # (540, 90)
    if touch_goal:
        seconds_passed = seconds_passed
    else:
        seconds_passed = (pygame.time.get_ticks() - start_ticks) / 1000

    text = font.render(f"Time: {seconds_passed}", True, (255, 255, 255))
    window.blit(text, (window.get_width()/10, window.get_height()/1.1))

    # display game over