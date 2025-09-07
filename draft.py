from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from math import sin, cos, atan2, radians, sqrt, pi
import random
import sys

GRID_LENGTH = 500
cam_angle_h = 45
cam_angle_v = 30
cam_dist = 4000
fovY = 60
GRID_STEP = 100
pause = False
show_trails = False
wireframe = False
enemies = []
projectiles = []
effects = []
wall_hp = {}
wall_max = {}
DEFENDED_CASTLE_ID = 0
defended_cfg = None
TOWER_TOP_Z = 800
lightPos = [0.0, 0.0, 1000.0, 1.0]
all_walls = []

class Wall:
    def __init__(self, x1, y1, x2, y2, thickness, height, owner):
        self.minx = min(x1, x2) - thickness / 2
        self.maxx = max(x1, x2) + thickness / 2
        self.miny = min(y1, y2) - thickness / 2
        self.maxy = max(y1, y2) + thickness / 2
        self.height = height
        self.owner = owner
        self.center = [(self.minx + self.maxx) / 2, (self.miny + self.maxy) / 2, height / 2]

    def intersects(self, pos):
        return self.minx < pos[0] < self.maxx and self.miny < pos[1] < self.maxy

# Castle configurations
castle_configs = [
    {
        'position': [-800, -1600, 0],
        'size': 1600,
        'height': 800,
        'tower_radius': 160,
        'floors': 7,
        'wall_thickness': 300,
        'wall_height': 600,
        'color_scheme': 'reddish'
    },
    {
        'position': [900, 1000, 0],
        'size': 1600,
        'height': 1200,
        'tower_radius': 180,
        'floors': 12,
        'wall_thickness': 400,
        'wall_height': 800,
        'color_scheme': 'reddish'
    },
    {
        'position': [-3300, 400, 0],
        'size': 2000,
        'height': 600,
        'tower_radius': 120,
        'floors': 3,
        'wall_thickness': 300,
        'wall_height': 450,
        'color_scheme': 'reddish'
    }
]

central_rock_pos = [-1000, 1500, 0]

def set_material(color, emission=(0.0, 0.0, 0.0)):
    glMaterialfv(GL_FRONT, GL_DIFFUSE, color + (1.0,))
    glMaterialfv(GL_FRONT, GL_SPECULAR, (0.5, 0.5, 0.5, 1.0))
    glMaterialfv(GL_FRONT, GL_EMISSION, emission + (1.0,))
    glMaterialfv(GL_FRONT, GL_SHININESS, 50.0)

def draw_box(width, depth, height):
    draw_cube_manual_shading(0, 0, height/2, width, depth, height, glGetFloatv(GL_CURRENT_COLOR)[:3])

def draw_sphere(radius):
    quad = gluNewQuadric()
    gluSphere(quad, radius, 16, 16)

def draw_cylinder(radius, height):
    quad = gluNewQuadric()
    gluCylinder(quad, radius, radius, height, 16, 16)

def check_collision(pos1, pos2, radius):
    dx = pos1[0] - pos2[0]
    dy = pos1[1] - pos2[1]
    dz = pos1[2] - pos2[2]
    return sqrt(dx*dx + dy*dy + dz*dz) < radius

class ParticleBurst:
    def __init__(self, pos, size=40, count=28):
        self.pos = pos[:]
        self.size = size
        self.count = count
        self.life = 1.0
        self.particles = []
        for _ in range(count):
            angle = random.uniform(0, 2*pi)
            speed = random.uniform(50, 150)
            vx = cos(angle) * speed
            vy = sin(angle) * speed
            vz = random.uniform(50, 200)
            self.particles.append({
                'pos': pos[:],
                'vel': [vx, vy, vz],
                'life': random.uniform(0.5, 1.5)
            })

    def update(self, dt):
        self.life -= dt
        for p in self.particles:
            p['pos'][0] += p['vel'][0] * dt
            p['pos'][1] += p['vel'][1] * dt
            p['pos'][2] += p['vel'][2] * dt - 500 * dt * dt
            p['life'] -= dt

    def draw(self):
        glDisable(GL_LIGHTING)
        glPointSize(5.0)
        glBegin(GL_POINTS)
        for p in self.particles:
            if p['life'] > 0:
                glColor3f(0.8, 0.8, 0.8)
                glVertex3f(p['pos'][0], p['pos'][1], p['pos'][2])
        glEnd()
        glPointSize(1.0)
        glEnable(GL_LIGHTING)

class Projectile:
    def __init__(self, pos, vel, radius=6.0, kind='arrow', damage=6):
        self.pos = pos[:]
        self.vel = vel[:]
        self.radius = radius
        self.kind = kind
        self.life = 5.0
        self.trail = []
        self.damage = damage

    def update(self, dt):
        self.life -= dt
        self.pos[0] += self.vel[0] * dt
        self.pos[1] += self.vel[1] * dt
        self.pos[2] += self.vel[2] * dt - 500 * dt * dt
        if show_trails:
            self.trail.append(self.pos[:])
            if len(self.trail) > 20:
                self.trail.pop(0)

    def draw(self):
        set_material((0.2, 0.2, 0.2) if self.kind == 'arrow' else (0.3, 0.3, 0.3))
        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], self.pos[2])
        draw_sphere(self.radius)
        glPopMatrix()
        if show_trails and self.trail:
            glDisable(GL_LIGHTING)
            glLineWidth(2.0)
            glBegin(GL_LINE_STRIP)
            glColor3f(0.5, 0.5, 0.5)
            for p in self.trail:
                glVertex3f(p[0], p[1], p[2])
            glEnd()
            glLineWidth(1.0)
            glEnable(GL_LIGHTING)

class Enemy:
    def __init__(self, pos, speed=200.0, attack_range=140, attack_rate=1.4, damage=8):
        self.pos = [float(pos[0]), float(pos[1]), float(pos[2])]
        self.speed = speed
        self.state = 'advance'
        self.attack_cool = 0.0
        self.hp = 100
        self.max_hp = 100
        self.attacking = False
        self.target_wall = None
        self.attack_range = attack_range
        self.attack_rate = attack_rate
        self.damage = damage

    def target_point(self):
        if self.target_wall:
            return self.target_wall.center
        cfg = defended_cfg
        x, y = cfg['position'][0], cfg['position'][1]
        size = cfg['size']
        wall_t = cfg['wall_thickness']
        half = size/2.0 + wall_t/2.0 + 100.0
        return [x, y-half, cfg['wall_height']*0.5]

    def update(self, dt):
        tp = self.target_point()
        delta = vec_to(self.pos, tp)
        d = norm(delta)
        if not self.attacking:
            if d > self.attack_range:
                dirx = delta[0] / d
                diry = delta[1] / d
                step = self.speed * dt
                new_x = self.pos[0] + dirx * step
                new_y = self.pos[1] + diry * step
                intersect_wall = None
                for wall in all_walls:
                    if wall.intersects([new_x, new_y, 0]):
                        intersect_wall = wall
                        break
                if intersect_wall:
                    self.attacking = True
                    self.target_wall = intersect_wall
                    self.attack_cool = 0.0
                else:
                    self.pos[0] = new_x
                    self.pos[1] = new_y
            else:
                self.attacking = True
                self.attack_cool = 0.0
        else:
            self.attack_cool -= dt
            if self.attack_cool <= 0:
                self.attack_cool = self.attack_rate
                owner = self.target_wall.owner if self.target_wall else DEFENDED_CASTLE_ID
                if owner in wall_hp:
                    wall_hp[owner] = max(0, wall_hp[owner] - self.damage)
                hit_pos = tp
                effects.append(ParticleBurst(hit_pos, size=40, count=28))

    def draw_hp_bar(self):
        if self.hp <= 0:
            return
        size = 60.0
        pct = max(0.0, self.hp/self.max_hp)
        eye = get_camera_eye()
        dir_cam = [eye[0]-self.pos[0], eye[1]-self.pos[1], eye[2]-(self.pos[2]+220)]
        rx = -dir_cam[1]
        ry = dir_cam[0]
        rz = 0.0
        rlen = sqrt(max(1e-6, rx*rx+ry*ry))
        rx /= rlen
        ry /= rlen
        ux = 0
        uy = 0
        uz = 1.0
        cx = self.pos[0]
        cy = self.pos[1]
        cz = self.pos[2] + 330.0
        glDisable(GL_LIGHTING)
        glColor3f(0.15, 0.15, 0.15)
        glBegin(GL_QUADS)
        glVertex3f(cx - rx*size - ux*6, cy - ry*size - uy*6, cz - uz*6)
        glVertex3f(cx + rx*size - ux*6, cy + ry*size - uy*6, cz - uz*6)
        glVertex3f(cx + rx*size + ux*6, cy + ry*size + uy*6, cz + uz*6)
        glVertex3f(cx - rx*size + ux*6, cy - ry*size + uy*6, cz + uz*6)
        glEnd()
        glColor3f(1.0-pct, pct, 0.1)
        glBegin(GL_QUADS)
        hw = size*0.98*pct
        glVertex3f(cx - rx*size, cy - ry*size, cz)
        glVertex3f(cx - rx*size + rx*hw, cy - ry*size + ry*hw, cz)
        glVertex3f(cx - rx*size + rx*hw + ux*6, cy - ry*size + ry*hw + uy*6, cz + uz*6)
        glVertex3f(cx - rx*size + ux*6, cy - ry*size + uy*6, cz + uz*6)
        glEnd()
        glEnable(GL_LIGHTING)

class Barbarian(Enemy):
    def __init__(self, pos):
        super().__init__(pos, speed=260.0, attack_range=140, attack_rate=1.4, damage=8)
        self.swing_phase = 0.0
        self.hp = 90
        self.max_hp = 90

    def update(self, dt):
        super().update(dt)
        if self.attacking:
            self.swing_phase += dt*6.0

    def draw(self):
        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], 0)
        set_material((0.8, 0.6, 0.5))  # Realistic skin color
        glPushMatrix()
        glTranslatef(-18, 0, 70)
        draw_box(20, 20, 140)
        glPopMatrix()
        glPushMatrix()
        glTranslatef(18, 0, 70)
        draw_box(20, 20, 140)
        glPopMatrix()
        set_material((0.4, 0.3, 0.2))  # Brown fur/leather
        glPushMatrix()
        glTranslatef(0, 0, 170)
        draw_box(80, 40, 140)
        glPopMatrix()
        set_material((0.8, 0.6, 0.5))  # Skin for head
        glPushMatrix()
        glTranslatef(0, 0, 260)
        draw_sphere(28)
        glPopMatrix()
        set_material((0.8, 0.6, 0.5))  # Skin for arms
        glPushMatrix()
        glTranslatef(40, 0, 190)
        draw_box(20, 20, 100)
        glPopMatrix()
        glPushMatrix()
        glTranslatef(-40, 0, 190)
        glRotatef(45*sin(self.swing_phase), 1, 0, 0)
        draw_box(20, 20, 100)
        glPopMatrix()
        glPushMatrix()
        glTranslatef(50, 0, 220)
        glRotatef(-70 + 60*sin(self.swing_phase), 1, 0, 0)
        set_material((0.5, 0.5, 0.5))  # Gray metal for hammer
        draw_cylinder(10, 100)
        glTranslatef(0, 0, 100)
        draw_box(30, 50, 30)
        glPopMatrix()
        glPopMatrix()
        self.draw_hp_bar()

class Giant(Enemy):
    def __init__(self, pos):
        super().__init__(pos, speed=150.0, attack_range=300, attack_rate=2.0, damage=22)
        self.swing = 0.0
        self.hp = 260
        self.max_hp = 260

    def update(self, dt):
        super().update(dt)
        if self.attacking:
            self.swing += dt*2.0

    def draw(self):
        scale = 2.0
        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], 0)
        glScalef(scale, scale, scale)
        set_material((0.6, 0.5, 0.4))  # Grayish skin for giant
        glPushMatrix()
        glTranslatef(-20, 0, 80)
        draw_box(26, 26, 160)
        glPopMatrix()
        glPushMatrix()
        glTranslatef(20, 0, 80)
        draw_box(26, 26, 160)
        glPopMatrix()
        set_material((0.3, 0.2, 0.15))  # Dark leather
        glPushMatrix()
        glTranslatef(0, 0, 200)
        draw_box(110, 50, 180)
        glPopMatrix()
        set_material((0.6, 0.5, 0.4))  # Skin for head
        glPushMatrix()
        glTranslatef(0, 0, 300)
        draw_sphere(36)
        glPopMatrix()
        set_material((0.6, 0.5, 0.4))  # Skin for arms
        glPushMatrix()
        glTranslatef(-70, 0, 220)
        glRotatef(30*sin(self.swing), 1, 0, 0)
        draw_box(26, 26, 140)
        glPopMatrix()
        glPushMatrix()
        glTranslatef(70, 0, 220)
        glRotatef(-30*sin(self.swing), 1, 0, 0)
        draw_box(26, 26, 140)
        glPopMatrix()
        glPopMatrix()
        self.draw_hp_bar()

class Archer(Enemy):
    def __init__(self, pos):
        super().__init__(pos, speed=240.0, attack_range=1200, attack_rate=random.uniform(1.0, 1.8), damage=6)
        self.reload = random.uniform(1.2, 2.0)
        self.hp = 70
        self.max_hp = 70

    def update(self, dt):
        super().update(dt)
        if self.attacking:
            self.reload -= dt
            if self.reload <= 0:
                self.reload = self.attack_rate
                tp = self.target_point()
                delta = vec_to(self.pos, tp)
                d = norm(delta)
                dirx, diry, dirz = delta[0]/d, delta[1]/d, delta[2]/d
                speed = 900.0
                proj_vel = [dirx*speed, diry*speed, dirz*speed + 180.0]
                projectiles.append(Projectile([self.pos[0], self.pos[1], 160.0], proj_vel, radius=6.0, kind='arrow', damage=self.damage))

    def draw(self):
        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], 0)
        set_material((0.3, 0.4, 0.2))  # Green tunic
        glPushMatrix()
        glTranslatef(-12, 0, 60)
        draw_box(16, 16, 120)
        glPopMatrix()
        glPushMatrix()
        glTranslatef(12, 0, 60)
        draw_box(16, 16, 120)
        glPopMatrix()
        set_material((0.25, 0.35, 0.15))  # Dark green body
        glPushMatrix()
        glTranslatef(0, 0, 150)
        draw_box(60, 30, 120)
        glPopMatrix()
        set_material((0.9, 0.7, 0.6))  # Skin head
        glPushMatrix()
        glTranslatef(0, 0, 220)
        draw_sphere(22)
        glPopMatrix()
        set_material((0.5, 0.3, 0.1))  # Brown bow
        glPushMatrix()
        glTranslatef(40, 0, 160)
        glRotatef(90, 0, 1, 0)
        draw_cylinder(3, 60)
        glPopMatrix()
        glPopMatrix()
        self.draw_hp_bar()

class Cannon(Enemy):
    def __init__(self, pos):
        super().__init__(pos, speed=160.0, attack_range=2200, attack_rate=random.uniform(2.0, 3.0), damage=30)
        self.reload = random.uniform(2.2, 3.4)
        self.hp = 120
        self.max_hp = 120

    def update(self, dt):
        super().update(dt)
        if self.attacking:
            self.reload -= dt
            if self.reload <= 0:
                self.reload = self.attack_rate
                tp = self.target_point()
                delta = vec_to(self.pos, tp)
                d = norm(delta)
                dirx, diry, dirz = delta[0]/d, delta[1]/d, delta[2]/d
                v0 = 1100.0
                projectiles.append(Projectile([self.pos[0], self.pos[1], 120.0], [dirx*v0, diry*v0, dirz*v0 + 200.0], radius=30.0, kind='ball', damage=self.damage))

    def draw(self):
        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], 0)
        set_material((0.2, 0.2, 0.2))  # Dark metal wheels
        for sx in (-40, 40):
            glPushMatrix()
            glTranslatef(sx, -24, 36)
            glRotatef(90, 0, 1, 0)
            draw_cylinder(22, 12)
            glPopMatrix()
            glPushMatrix()
            glTranslatef(sx, 24, 36)
            glRotatef(90, 0, 1, 0)
            draw_cylinder(22, 12)
            glPopMatrix()
        set_material((0.4, 0.25, 0.1))  # Brown wood base
        glPushMatrix()
        glTranslatef(0, 0, 40)
        draw_box(160, 80, 40)
        glPopMatrix()
        set_material((0.2, 0.2, 0.2))  # Metal cannon
        glPushMatrix()
        glTranslatef(0, 0, 90)
        glRotatef(10, 1, 0, 0)
        draw_cylinder(20, 140)
        glPopMatrix()
        glPopMatrix()
        self.draw_hp_bar()

SPAWN_RADIUS = 6000.0
spawn_flags = {'barbarian': True, 'archer': True, 'giant': True, 'cannon': True}
spawn_timers = {'barbarian': 0.0, 'archer': 0.0, 'giant': 0.0, 'cannon': 0.0}

def vec_to(a, b):
    return [b[0]-a[0], b[1]-a[1], b[2]-a[2]]

def norm(v):
    return sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])

def rand_spawn_pos():
    a = random.uniform(0, 2*pi)
    return [cos(a)*SPAWN_RADIUS, sin(a)*SPAWN_RADIUS, 0.0]

def spawn_enemy(kind):
    pos = rand_spawn_pos()
    if kind == 'barbarian':
        enemies.append(Barbarian(pos))
    elif kind == 'archer':
        enemies.append(Archer(pos))
    elif kind == 'giant':
        enemies.append(Giant(pos))
    elif kind == 'cannon':
        enemies.append(Cannon(pos))

def update_spawning(dt):
    spawn_timers['barbarian'] -= dt
    if spawn_flags['barbarian'] and spawn_timers['barbarian'] <= 0:
        spawn_timers['barbarian'] = random.uniform(1.0, 2.5)
        enemies.append(Barbarian(rand_spawn_pos()))
    spawn_timers['archer'] -= dt
    if spawn_flags['archer'] and spawn_timers['archer'] <= 0:
        spawn_timers['archer'] = random.uniform(2.2, 3.5)
        enemies.append(Archer(rand_spawn_pos()))
    spawn_timers['giant'] -= dt
    if spawn_flags['giant'] and spawn_timers['giant'] <= 0:
        spawn_timers['giant'] = random.uniform(4.0, 7.0)
        enemies.append(Giant(rand_spawn_pos()))
    spawn_timers['cannon'] -= dt
    if spawn_flags['cannon'] and spawn_timers['cannon'] <= 0:
        spawn_timers['cannon'] = random.uniform(5.0, 8.0)
        enemies.append(Cannon(rand_spawn_pos()))

def get_camera_eye():
    th = radians(cam_angle_h)
    ph = radians(cam_angle_v)
    cx = cos(th)*cos(ph)*cam_dist
    cy = sin(th)*cos(ph)*cam_dist
    cz = sin(ph)*cam_dist
    target = [defended_cfg['position'][0], defended_cfg['position'][1], defended_cfg['wall_height']]
    return [cx+target[0], cy+target[1], cz+target[2]]

def draw_hp_bar_for_castle(cfg_id):
    if cfg_id not in wall_hp:
        return
    cfg = castle_configs[cfg_id]
    cx, cy, _ = cfg['position']
    posx = cx
    posy = cy
    posz = cfg['height'] + cfg['wall_height'] + 180.0
    hp = wall_hp[cfg_id]
    hpmax = wall_max[cfg_id]
    pct = hp / float(hpmax) if hpmax > 0 else 0.0
    glDisable(GL_LIGHTING)
    glColor3f(0.15, 0.15, 0.15)
    glBegin(GL_QUADS)
    glVertex3f(posx-150, posy, posz)
    glVertex3f(posx+150, posy, posz)
    glVertex3f(posx+150, posy, posz+16)
    glVertex3f(posx-150, posy, posz+16)
    glEnd()
    glColor3f(1.0-pct, pct, 0.1)
    glBegin(GL_QUADS)
    glVertex3f(posx-148, posy+0.1, posz+2)
    glVertex3f(posx-148 + 296*pct, posy+0.1, posz+2)
    glVertex3f(posx-148 + 296*pct, posy+0.1, posz+14)
    glVertex3f(posx-148, posy+0.1, posz+14)
    glEnd()
    glEnable(GL_LIGHTING)

def get_color_scheme(scheme_name, base_color):
    if scheme_name == 'reddish':
        return [min(1.0, base_color[0] * 1.2), base_color[1] * 0.8, base_color[2] * 0.8]
    else:
        return base_color

def draw_cube_manual_shading(x, y, z, dx, dy, dz, base_color):
    glPushMatrix()
    glTranslatef(x, y, z)
    top_color = [min(1.0, c * 1.3) for c in base_color]
    front_color = base_color
    side_color = [c * 0.7 for c in base_color]
    back_color = [c * 0.5 for c in base_color]
    glBegin(GL_QUADS)
    glColor3f(top_color[0], top_color[1], top_color[2])
    glVertex3f(-dx/2, dy/2, -dz/2)
    glVertex3f(-dx/2, dy/2, dz/2)
    glVertex3f(dx/2, dy/2, dz/2)
    glVertex3f(dx/2, dy/2, -dz/2)
    glColor3f(front_color[0], front_color[1], front_color[2])
    glVertex3f(-dx/2, -dy/2, dz/2)
    glVertex3f(dx/2, -dy/2, dz/2)
    glVertex3f(dx/2, dy/2, dz/2)
    glVertex3f(-dx/2, dy/2, dz/2)
    glColor3f(side_color[0], side_color[1], side_color[2])
    glVertex3f(dx/2, -dy/2, -dz/2)
    glVertex3f(dx/2, dy/2, -dz/2)
    glVertex3f(dx/2, dy/2, dz/2)
    glVertex3f(dx/2, -dy/2, dz/2)
    glColor3f(side_color[0], side_color[1], side_color[2])
    glVertex3f(-dx/2, -dy/2, -dz/2)
    glVertex3f(-dx/2, -dy/2, dz/2)
    glVertex3f(-dx/2, dy/2, dz/2)
    glVertex3f(-dx/2, dy/2, -dz/2)
    glColor3f(back_color[0], back_color[1], back_color[2])
    glVertex3f(-dx/2, -dy/2, -dz/2)
    glVertex3f(-dx/2, dy/2, -dz/2)
    glVertex3f(dx/2, dy/2, -dz/2)
    glVertex3f(dx/2, -dy/2, -dz/2)
    glColor3f(side_color[0], side_color[1], side_color[2])
    glVertex3f(-dx/2, -dy/2, -dz/2)
    glVertex3f(dx/2, -dy/2, -dz/2)
    glVertex3f(dx/2, -dy/2, dz/2)
    glVertex3f(-dx/2, -dy/2, dz/2)
    glEnd()
    glPopMatrix()

def init_walls():
    global all_walls
    all_walls = []
    # Perimeter walls
    wall_thickness = 200
    wall_height = 400
    buildings_to_encapsulate = [
        castle_configs[0],
        castle_configs[2],
        {'position': central_rock_pos, 'size': 800}
    ]
    min_x = min([pos['position'][0] - pos['size']/2 for pos in buildings_to_encapsulate]) - 500
    max_x = max([pos['position'][0] + pos['size']/2 for pos in buildings_to_encapsulate]) + 500
    min_y = min([pos['position'][1] - pos['size']/2 for pos in buildings_to_encapsulate]) - 500
    max_y = max([pos['position'][1] + pos['size']/2 for pos in buildings_to_encapsulate]) + 500
    wall_segments = [
        (min_x, max_y, max_x, max_y),
        (max_x, max_y, max_x, min_y),
        (max_x, min_y, min_x, min_y),
        (min_x, min_y, min_x, max_y)
    ]
    for x1, y1, x2, y2 in wall_segments:
        all_walls.append(Wall(x1, y1, x2, y2, wall_thickness, wall_height, 'perimeter'))
    # Castle walls
    for i, config in enumerate(castle_configs):
        pos = config['position']
        size = config['size']
        wall_thickness = config['wall_thickness']
        wall_height = config['wall_height']
        half_size = size / 2
        corners = [
            (pos[0] + half_size, pos[1] + half_size),
            (pos[0] - half_size, pos[1] + half_size),
            (pos[0] - half_size, pos[1] - half_size),
            (pos[0] + half_size, pos[1] - half_size)
        ]
        wall_inset = 50
        for j in range(len(corners)):
            x1, y1 = corners[j]
            x2, y2 = corners[(j + 1) % len(corners)]
            dx, dy = x2 - x1, y2 - y1
            length = (dx**2 + dy**2)**0.5
            if length > 0:
                dx_norm, dy_norm = dx / length * wall_inset, dy / length * wall_inset
            else:
                dx_norm, dy_norm = 0, 0
            wall_x1, wall_y1 = x1 + dx_norm, y1 + dy_norm
            wall_x2, wall_y2 = x2 - dx_norm, y2 - dy_norm
            all_walls.append(Wall(wall_x1, wall_y1, wall_x2, wall_y2, wall_thickness, wall_height, i))



def draw_perimeter_wall():
    wall_thickness = 200
    wall_height = 400
    wall_color = [0.7, 0.7, 0.6]
    buildings_to_encapsulate = [
        castle_configs[0],
        castle_configs[2],
        {'position': central_rock_pos, 'size': 800}
    ]
    min_x = min([pos['position'][0] - pos['size']/2 for pos in buildings_to_encapsulate]) - 500
    max_x = max([pos['position'][0] + pos['size']/2 for pos in buildings_to_encapsulate]) + 500
    min_y = min([pos['position'][1] - pos['size']/2 for pos in buildings_to_encapsulate]) - 500
    max_y = max([pos['position'][1] + pos['size']/2 for pos in buildings_to_encapsulate]) + 500
    wall_segments = [
        (min_x, max_y, max_x, max_y),
        (max_x, max_y, max_x, min_y),
        (max_x, min_y, min_x, min_y),
        (min_x, min_y, min_x, max_y)
    ]
    for x1, y1, x2, y2 in wall_segments:
        draw_wall_segment(x1, y1, x2, y2, 0, wall_thickness, wall_height, wall_color)
        draw_perimeter_stone_blocks(x1, y1, x2, y2, 0, wall_thickness, wall_height)
    corners = set()
    for x1, y1, x2, y2 in wall_segments:
        corners.add((x1, y1))
        corners.add((x2, y2))
    for corner_x, corner_y in corners:
        draw_guard_tower(corner_x, corner_y, wall_height)

def draw_wall_segment(x1, y1, x2, y2, offset_z, thickness, height, color):
    midx = (x1 + x2) / 2
    midy = (y1 + y2) / 2
    length = ((x2 - x1)**2 + (y2 - y1)**2) ** 0.5
    glPushMatrix()
    glTranslatef(midx, midy, offset_z + height/2)
    angle = atan2(y2 - y1, x2 - x1) * 180 / 3.14159
    glRotatef(angle, 0, 0, 1)
    draw_cube_manual_shading(0, 0, 0, length, thickness, height, color)
    glPopMatrix()

def draw_perimeter_stone_blocks(x1, y1, x2, y2, offset_z, thickness, height):
    length = ((x2 - x1)**2 + (y2 - y1)**2) ** 0.5
    angle = atan2(y2 - y1, x2 - x1) * 180 / 3.14159
    block_width, block_height, gap = 150, 80, 15
    blocks_x = int(length / (block_width + gap))
    blocks_z = int(height / (block_height + gap))
    midx, midy = (x1 + x2) / 2, (y1 + y2) / 2
    for row in range(blocks_z):
        for col in range(blocks_x):
            offset = (block_width + gap) / 2 if (row % 2 == 1) else 0
            block_x_local = -length/2 + col * (block_width + gap) + block_width/2 + offset
            block_z_local = row * (block_height + gap) + block_height/2
            if abs(block_x_local) > length/2 - block_width/2:
                continue
            cos_a, sin_a = cos(radians(angle)), sin(radians(angle))
            world_x = midx + block_x_local * cos_a
            world_y = midy + block_x_local * sin_a
            world_z = offset_z + block_z_local + 15
            base_r, base_g, base_b = 0.75, 0.75, 0.65
            variation = 0.1 * ((row + col) % 4 - 2) / 2
            block_color = [
                min(max(base_r + variation, 0.0), 1.0),
                min(max(base_g + variation, 0.0), 1.0),
                min(max(base_b + variation, 0.0), 1.0)
            ]
            glPushMatrix()
            glTranslatef(world_x, world_y, world_z)
            glRotatef(angle, 0, 0, 1)
            draw_cube_manual_shading(0, 0, 0, block_width, thickness + 5, block_height, block_color)
            glPopMatrix()

def draw_guard_tower(x, y, wall_height):
    tower_radius = 60
    tower_height = wall_height + 200
    tower_color = [0.6, 0.6, 0.55]
    quad = gluNewQuadric()
    glPushMatrix()
    glTranslatef(x, y, 0)
    glColor3f(tower_color[0], tower_color[1], tower_color[2])
    gluCylinder(quad, tower_radius, tower_radius, tower_height, 16, 16)
    glTranslatef(0, 0, tower_height)
    roof_color = [0.8, 0.3, 0.2]
    glColor3f(roof_color[0], roof_color[1], roof_color[2])
    gluCylinder(quad, tower_radius + 10, 5, tower_radius, 12, 12)
    glPopMatrix()
    battlement_color = [0.5, 0.5, 0.45]
    for angle in range(0, 360, 30):
        rad = radians(angle)
        bx = x + (tower_radius + 15) * cos(rad)
        by = y + (tower_radius + 15) * sin(rad)
        draw_cube_manual_shading(bx, by, wall_height + 150, 20, 20, 50, battlement_color)

def draw_rope(start_pos, end_pos, segments=20):
    x1, y1, z1 = start_pos
    x2, y2, z2 = end_pos
    glColor3f(0.4, 0.3, 0.2)
    glLineWidth(3.0)
    distance = sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)
    sag_factor = min(100, distance * 0.1)
    glBegin(GL_LINE_STRIP)
    for i in range(segments + 1):
        t = i / segments
        x = x1 + t * (x2 - x1)
        y = y1 + t * (y2 - y1)
        z = z1 + t * (z2 - z1)
        sag = sag_factor * (4 * t * (1 - t))
        z -= sag
        glVertex3f(x, y, z)
    glEnd()
    glLineWidth(1.0)

def draw_rope_support_bar(x, y, z, height=200):
    glColor3f(0.3, 0.3, 0.3)
    bar_radius = 8
    quad = gluNewQuadric()
    glPushMatrix()
    glTranslatef(x, y, z)
    gluCylinder(quad, bar_radius, bar_radius, height, 16, 16)
    glTranslatef(0, 0, height)
    gluDisk(quad, 0, bar_radius, 16, 1)
    glTranslatef(0, 0, 5)
    glRotatef(90, 0, 1, 0)
    gluCylinder(quad, 5, 5, 30, 8, 8)
    glPopMatrix()

def draw_platform_with_gap(x, y, z, radius, gap_angle_start=0, gap_angle_end=45, color_scheme='normal'):
    platform_thickness = 20
    base_color = [0.7, 0.7, 0.65]
    platform_color = get_color_scheme(color_scheme, base_color)
    glPushMatrix()
    glTranslatef(x, y, z + platform_thickness/2)
    glColor3f(platform_color[0], platform_color[1], platform_color[2])
    segments = 36
    segment_angle = 360 / segments
    for i in range(segments):
        current_angle = i * segment_angle
        next_angle = (i + 1) * segment_angle
        if not (gap_angle_start <= current_angle <= gap_angle_end):
            glBegin(GL_TRIANGLES)
            glVertex3f(0, 0, 0)
            rad1 = radians(current_angle)
            glVertex3f(radius * cos(rad1), radius * sin(rad1), 0)
            rad2 = radians(next_angle)
            glVertex3f(radius * cos(rad2), radius * sin(rad2), 0)
            glEnd()
    glPopMatrix()
    battlement_base = [0.55, 0.55, 0.55]
    battlement_color = get_color_scheme(color_scheme, battlement_base)
    battlement_z = z + platform_thickness
    for angle in range(0, 360, 20):
        if not (gap_angle_start <= angle <= gap_angle_end):
            rad = radians(angle)
            bx = x + (radius + 25) * cos(rad)
            by = y + (radius + 25) * sin(rad)
            draw_cube_manual_shading(bx, by, battlement_z + 30, 35, 35, 80, battlement_color)

def draw_tower_with_platform(offset_x, offset_y, offset_z, radius=160, height=800, floors=3, color_scheme='normal'):
    quad = gluNewQuadric()
    glPushMatrix()
    glTranslatef(offset_x, offset_y, offset_z)
    base_stone_color = [0.82, 0.8, 0.72]
    stone_color = get_color_scheme(color_scheme, base_stone_color)
    glColor3f(stone_color[0], stone_color[1], stone_color[2])
    floor_height = height / floors
    for floor in range(floors):
        gluCylinder(quad, radius, radius, floor_height, 32, 32)
        glTranslatef(0, 0, floor_height)
        if floor < floors - 1:
            ring_base = [0.6, 0.6, 0.6]
            ring_color = get_color_scheme(color_scheme, ring_base)
            glColor3f(ring_color[0], ring_color[1], ring_color[2])
            gluCylinder(quad, radius + 5, radius + 5, 10, 32, 32)
            glColor3f(stone_color[0], stone_color[1], stone_color[2])
            glTranslatef(0, 0, 10)
    glPopMatrix()
    platform_z = offset_z + height
    platform_radius = radius + 30
    gap_start = 315
    gap_end = 45
    draw_platform_with_gap(offset_x, offset_y, platform_z, platform_radius, gap_start, gap_end, color_scheme)
    central_base = [0.8, 0.8, 0.75]
    central_color = get_color_scheme(color_scheme, central_base)
    draw_cube_manual_shading(offset_x, offset_y, platform_z + 40, 60, 60, 80, central_color)

def draw_rock_tower():
    x, y, z = central_rock_pos
    rock_color = [0.4, 0.4, 0.35]
    draw_cube_manual_shading(x, y, z + 256, 352, 330, 413, rock_color)
    draw_cube_manual_shading(x - 15, y + 8, z + 650, 308, 286, 375, rock_color)
    draw_cube_manual_shading(x + 12, y - 10, z + 1006, 264, 242, 338, rock_color)
    draw_cube_manual_shading(x - 5, y + 5, z + 1300, 220, 198, 250, rock_color)
    draw_cube_manual_shading(x, y, z + 1488, 165, 154, 125, rock_color)

def draw_rock_tower_platform():
    x, y, z = central_rock_pos
    platform_height = z + 1600
    platform_radius = 120
    platform_thickness = 30
    platform_color = [0.6, 0.6, 0.55]
    glColor3f(platform_color[0], platform_color[1], platform_color[2])
    draw_filled_circle(x, y, platform_height + platform_thickness/2, platform_radius)
    railing_color = [0.5, 0.5, 0.45]
    railing_height = platform_height + platform_thickness + 10
    for angle in range(0, 360, 30):
        rad = radians(angle)
        rail_x = x + (platform_radius - 10) * cos(rad)
        rail_y = y + (platform_radius - 10) * sin(rad)
        draw_cube_manual_shading(rail_x, rail_y, railing_height + 15, 8, 8, 30, railing_color)

def draw_filled_circle(x, y, z, radius, segments=32):
    glPushMatrix()
    glTranslatef(x, y, z)
    glBegin(GL_TRIANGLE_FAN)
    glVertex3f(0.0, 0.0, 0.0)
    for i in range(segments + 1):
        angle = 2 * 3.14159 * i / segments
        px = radius * cos(angle)
        py = radius * sin(angle)
        glVertex3f(px, py, 0.0)
    glEnd()
    glPopMatrix()

def draw_spiral_stairs_around_rock():
    x, y, z = central_rock_pos
    radius = 220
    steps = 80
    total_height = 1600
    height_per_step = total_height / steps
    angle_per_step = 1800 / steps
    stair_color = [0.6, 0.5, 0.4]
    for i in range(steps):
        angle = radians(angle_per_step * i)
        step_x = x + radius * cos(angle)
        step_y = y + radius * sin(angle)
        step_z = z + height_per_step * i
        glPushMatrix()
        glTranslatef(step_x, step_y, step_z)
        glRotatef(angle_per_step * i, 0, 0, 1)
        draw_cube_manual_shading(0, 0, 0, 100, 50, 15, stair_color)
        if i % 10 == 0:
            draw_cube_manual_shading(0, 0, -50, 25, 25, 100, stair_color)
        glPopMatrix()

def draw_rope_connections():
    for config in castle_configs:
        pos = config['position']
        size = config['size']
        wall_height = config['wall_height']
        castle_center_height = pos[2] + wall_height
        castle_center = [pos[0], pos[1], castle_center_height]
        bar_height = 350
        draw_rope_support_bar(castle_center[0], castle_center[1], castle_center[2], bar_height)
        center_bar_top = [castle_center[0], castle_center[1], castle_center[2] + bar_height - 50]
        rock_platform = [central_rock_pos[0], central_rock_pos[1], central_rock_pos[2] + 1600 + 150]
        draw_rope(center_bar_top, rock_platform)
    draw_rope_support_bar(central_rock_pos[0], central_rock_pos[1], central_rock_pos[2] + 1600 + 30, 100)

def draw_wall(x1, y1, x2, y2, offset_z, thickness=400, height=600, color_scheme='normal'):
    midx = (x1 + x2) / 2
    midy = (y1 + y2) / 2
    length = ((x2 - x1)**2 + (y2 - y1)**2) ** 0.5
    glPushMatrix()
    glTranslatef(midx, midy, offset_z + height/2)
    angle = atan2(y2 - y1, x2 - x1) * 180 / 3.14159
    glRotatef(angle, 0, 0, 1)
    wall_base = [0.85, 0.82, 0.75]
    wall_color = get_color_scheme(color_scheme, wall_base)
    draw_cube_manual_shading(0, 0, 0, length, thickness, height, wall_color)
    glPopMatrix()

def draw_stone_block(x, y, z, width, depth, height, angle, row, col, color_scheme='normal'):
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(angle, 0, 0, 1)
    base_r, base_g, base_b = 0.85, 0.40, 0.35
    variation = 0.12 * ((row + col) % 5 - 2) / 2
    stone_color = [
        min(max(base_r + variation, 0.0), 1.0),
        min(max(base_g + variation, 0.0), 1.0),
        min(max(base_b + variation, 0.0), 1.0)
    ]
    final_color = get_color_scheme(color_scheme, stone_color)
    draw_cube_manual_shading(0, 0, 0, width, depth, height, final_color)
    glPopMatrix()

def draw_stone_blocks(x1, y1, x2, y2, offset_z, thickness, height, color_scheme='normal'):
    length = ((x2 - x1)**2 + (y2 - y1)**2) ** 0.5
    angle = atan2(y2 - y1, x2 - x1) * 180 / 3.14159
    block_width, block_height, gap = 200, 100, 20
    blocks_x = int(length / (block_width + gap))
    blocks_z = int(height / (block_height + gap))
    midx, midy = (x1 + x2) / 2, (y1 + y2) / 2
    for row in range(blocks_z):
        for col in range(blocks_x):
            offset = (block_width + gap) / 2 if (row % 2 == 1) else 0
            block_x_local = -length/2 + col * (block_width + gap) + block_width/2 + offset
            block_z_local = row * (block_height + gap) + block_height/2
            if abs(block_x_local) > length/2 - block_width/2:
                continue
            cos_a, sin_a = cos(radians(angle)), sin(radians(angle))
            world_x = midx + block_x_local * cos_a
            world_y = midy + block_x_local * sin_a
            world_z = offset_z + block_z_local + 15
            draw_stone_block(world_x, world_y, world_z, block_width, thickness + 5, block_height, angle, row, col, color_scheme)

def draw_single_castle(config):
    pos = config['position']
    size = config['size']
    height = config['height']
    tower_radius = config['tower_radius']
    floors = config['floors']
    wall_thickness = config['wall_thickness']
    wall_height = config['wall_height']
    color_scheme = config['color_scheme']
    half_size = size / 2
    corners = [
        (pos[0] + half_size, pos[1] + half_size),
        (pos[0] - half_size, pos[1] + half_size),
        (pos[0] - half_size, pos[1] - half_size),
        (pos[0] + half_size, pos[1] - half_size)
    ]
    for (x, y) in corners:
        draw_tower_with_platform(x, y, pos[2], tower_radius, height, floors, color_scheme)
    wall_inset = 50
    for i in range(len(corners)):
        x1, y1 = corners[i]
        x2, y2 = corners[(i + 1) % len(corners)]
        dx, dy = x2 - x1, y2 - y1
        length = (dx**2 + dy**2)**0.5
        dx_norm, dy_norm = dx / length * wall_inset, dy / length * wall_inset
        wall_x1, wall_y1 = x1 + dx_norm, y1 + dy_norm
        wall_x2, wall_y2 = x2 - dx_norm, y2 - dy_norm
        draw_wall(wall_x1, wall_y1, wall_x2, wall_y2, pos[2], wall_thickness, wall_height, color_scheme)
        draw_stone_blocks(wall_x1, wall_y1, wall_x2, wall_y2, pos[2], wall_thickness, wall_height, color_scheme)
    railing_height = 80
    railing_color = get_color_scheme(color_scheme, [0.6, 0.6, 0.55])
    railing_top_z = pos[2] + wall_height + railing_height/2
    for i in range(len(corners)):
        x1, y1 = corners[i]
        x2, y2 = corners[(i + 1) % len(corners)]
        dx, dy = x2 - x1, y2 - y1
        length = (dx**2 + dy**2)**0.5
        dx_norm, dy_norm = dx / length * wall_inset, dy / length * wall_inset
        wall_x1, wall_y1 = x1 + dx_norm, y1 + dy_norm
        wall_x2, wall_y2 = x2 - dx_norm, y2 - dy_norm
        num_railings = int(length / 100)
        for j in range(num_railings + 1):
            t = j / max(num_railings, 1)
            rail_x = wall_x1 + t * (wall_x2 - wall_x1)
            rail_y = wall_y1 + t * (wall_y2 - wall_y1)
            draw_cube_manual_shading(rail_x, rail_y, railing_top_z, 15, 15, railing_height, railing_color)
        midx = (wall_x1 + wall_x2) / 2
        midy = (wall_y1 + wall_y2) / 2
        glPushMatrix()
        glTranslatef(midx, midy, pos[2] + wall_height + railing_height - 20)
        angle = atan2(wall_y2 - wall_y1, wall_x2 - wall_x1) * 180 / 3.14159
        glRotatef(angle, 0, 0, 1)
        railing_bar_color = get_color_scheme(color_scheme, [0.65, 0.65, 0.6])
        draw_cube_manual_shading(0, 0, 0, length - 2*wall_inset, 10, 8, railing_bar_color)
        glPopMatrix()
    interior_base = [0.82, 0.8, 0.72]
    gate_base = [0.3, 0.3, 0.3]
    interior_color = get_color_scheme(color_scheme, interior_base)
    gate_color = get_color_scheme(color_scheme, gate_base)
    draw_cube_manual_shading(pos[0], pos[1], pos[2] + wall_height/2, size * 0.8, size * 0.8, wall_height, interior_color)
    draw_cube_manual_shading(pos[0], pos[1] - half_size + wall_inset, pos[2] + wall_height/2, 300, 80, wall_height, gate_color)

def draw_simple_tree(x, y, z, size=100):
    quad = gluNewQuadric()
    glPushMatrix()
    glTranslatef(x, y, z)
    glColor3f(0.4, 0.2, 0.1)
    gluCylinder(quad, size*0.15, size*0.1, size*0.8, 6, 10)
    glTranslatef(0, 0, size*0.6)
    glColor3f(0.1, 0.5, 0.1)
    gluSphere(quad, size*0.6, 8, 8)
    glPopMatrix()

def draw_simple_bush(x, y, z, size=60):
    quad = gluNewQuadric()
    glPushMatrix()
    glTranslatef(x, y, z + size*0.4)
    glColor3f(0.2, 0.4, 0.2)
    gluSphere(quad, size*0.5, 6, 6)
    glPopMatrix()

def draw_multi_colored_grid():
    grid_size = GRID_LENGTH * 20
    quad_size = 800
    num_quads = (grid_size * 2) // quad_size
    green_colors = [
        [0.15, 0.4, 0.15],
        [0.2, 0.5, 0.2],
        [0.25, 0.6, 0.25],
        [0.3, 0.7, 0.3],
        [0.35, 0.75, 0.35],
        [0.4, 0.8, 0.4],
        [0.2, 0.45, 0.2],
        [0.18, 0.55, 0.18]
    ]
    for i in range(num_quads):
        for j in range(num_quads):
            x1 = -grid_size + i * quad_size
            y1 = -grid_size + j * quad_size
            x2 = x1 + quad_size
            y2 = y1 + quad_size
            color_index = (i + j) % len(green_colors)
            color = green_colors[color_index]
            glColor3f(color[0], color[1], color[2])
            glBegin(GL_QUADS)
            glVertex3f(x1, y1, 0)
            glVertex3f(x2, y1, 0)
            glVertex3f(x2, y2, 0)
            glVertex3f(x1, y2, 0)
            glEnd()
    glColor3f(0.1, 0.3, 0.1)
    glLineWidth(1.0)
    glBegin(GL_LINES)
    for i in range(num_quads + 1):
        line_x = -grid_size + i * quad_size
        glVertex3f(line_x, -grid_size, 1)
        glVertex3f(line_x, grid_size, 1)
    for j in range(num_quads + 1):
        line_y = -grid_size + j * quad_size
        glVertex3f(-grid_size, line_y, 1)
        glVertex3f(grid_size, line_y, 1)
    glEnd()

def draw_minimal_vegetation():
    tree_positions = [
        (-5000, -3000), (-4000, 2000), (-2000, -4000), (3000, -2000), (4000, 3000),
        (-6000, 1000), (2000, -5000), (5000, -1000), (-1000, -6000), (6000, 2000),
        (-3000, 4000), (1000, 5000), (-5000, 0), (0, -3000), (4000, 0)
    ]
    bush_positions = [
        (-4500, -2500), (-3500, 1500), (-1500, -3500), (2500, -1500), (3500, 2500),
        (-5500, 500), (1500, -4500), (4500, -500), (-500, -5500), (5500, 1500),
        (-2500, 3500), (500, 4500), (-4500, -500), (-500, -2500), (3500, -500),
        (-1500, 4500), (4500, 500), (-3500, -1500), (2500, 3500), (-500, 5500),
        (-6000, -1000), (1000, -6000), (6000, 1000), (-1000, 6000), (0, -4000)
    ]
    def is_safe_position(x, y):
        castle_centers = [[-800, -1600], [900, 1000], [-3300, 400], [-1000, 1500]]
        for cx, cy in castle_centers:
            if sqrt((x - cx)**2 + (y - cy)**2) < 900:
                return False
        return True
    for x, y in tree_positions:
        if is_safe_position(x, y):
            draw_simple_tree(x, y, 30, 240)
    for x, y in bush_positions:
        if is_safe_position(x, y):
            draw_simple_bush(x, y, 0, 190)

def draw_mountain_range():
    mountain_positions = [
        (-2746, 6714, 0, 825, 1079, 740),
        (-1150, 8828, 0, 942, 1077, 652),
        (-2708, 7358, 0, 1358, 744, 816),
        (-1368, 8630, 0, 895, 811, 719),
        (-2883, 7216, 0, 827, 987, 701),
        (-1100, 9100, 0, 1200, 900, 800),
        (-2600, 6900, 0, 1000, 850, 750),
        (-167, -6735, 0, 1358, 914, 712),
        (-2441, -8797, 0, 1084, 703, 681),
        (-186, -6968, 0, 1148, 842, 679),
        (-2680, -8619, 0, 1144, 752, 647),
        (-511, -7301, 0, 1167, 876, 735),
        (-2300, -8800, 0, 1100, 800, 700),
        (-800, -7000, 0, 900, 750, 650),
        (6644, -1653, 0, 1270, 974, 663),
        (8987, -320, 0, 1365, 850, 785),
        (7191, -2204, 0, 871, 723, 716),
        (9391, -104, 0, 881, 819, 651),
        (6989, -2116, 0, 1264, 1025, 786),
        (9100, 200, 0, 1000, 900, 750),
        (6800, -2000, 0, 1200, 850, 700),
        (-7234, 479, 0, 1163, 807, 736),
        (-8682, -1201, 0, 873, 1011, 687),
        (-6854, 846, 0, 1050, 783, 836),
        (-9012, -1624, 0, 1370, 812, 766),
        (-6614, 894, 0, 857, 817, 616),
        (-8900, -1400, 0, 1100, 950, 800),
        (-7200, 700, 0, 950, 800, 650),
        (5000, 4500, 0, 1000, 800, 700),
        (7300, 6800, 0, 850, 750, 650),
        (4800, 4600, 0, 1200, 900, 800),
        (7100, 6300, 0, 950, 850, 750),
        (-7000, 4500, 0, 1100, 900, 750),
        (-5400, 6800, 0, 900, 800, 700),
        (-6700, 4600, 0, 1250, 950, 850),
        (-5200, 6200, 0, 1000, 850, 750),
        (5000, -6500, 0, 1050, 850, 700),
        (7300, -4200, 0, 950, 800, 650),
        (4800, -6800, 0, 1150, 900, 750),
        (7100, -4600, 0, 900, 750, 700),
        (-7000, -6500, 0, 1200, 950, 800),
        (-5300, -4800, 0, 800, 700, 600),
        (-6700, -6300, 0, 1100, 900, 750),
        (-5100, -4600, 0, 950, 800, 700),
    ]
    for x, y, z, width, height, depth in mountain_positions:
        draw_rocky_mountain(x, y, z, width, height, depth)

def draw_rocky_mountain(x, y, z, width=800, height=600, depth=600):
    quad = gluNewQuadric()
    base_color = [0.5, 0.4, 0.35]
    glPushMatrix()
    glTranslatef(x, y, z)
    glColor3f(base_color[0], base_color[1], base_color[2])
    glPushMatrix()
    glScalef(width/200, depth/200, height/200)
    gluSphere(quad, 100, 12, 8)
    glPopMatrix()
    glPopMatrix()

def draw_all_structures():
    for config in castle_configs:
        draw_single_castle(config)
    draw_rock_tower()
    draw_rock_tower_platform()
    draw_spiral_stairs_around_rock()
    draw_rope_connections()
    draw_perimeter_wall()

def draw_text(x, y, text, font=None):
    glColor3f(1, 1, 1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    try:
        font = font or GLUT_BITMAP_HELVETICA_18
    except NameError:
        print("Warning: GLUT_BITMAP_HELVETICA_18 not defined, using GLUT_BITMAP_9_BY_15")
        font = GLUT_BITMAP_9_BY_15
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def setup_camera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, 1.25, 0.1, 30000)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    th = radians(cam_angle_h)
    ph = radians(cam_angle_v)
    cx = cos(th)*cos(ph)*cam_dist
    cy = sin(th)*cos(ph)*cam_dist
    cz = sin(ph)*cam_dist
    target = [defended_cfg['position'][0], defended_cfg['position'][1], defended_cfg['wall_height']]
    gluLookAt(cx+target[0], cy+target[1], cz+target[2], target[0], target[1], target[2], 0, 0, 1)

prev_time = None
def update():
    global prev_time
    t = glutGet(GLUT_ELAPSED_TIME) / 1000.0
    if prev_time is None:
        prev_time = t
    dt = min(0.04, max(0.001, t - prev_time))
    prev_time = t
    if not pause:
        update_spawning(dt)
        for e in list(enemies):
            e.update(dt)
            if e.hp <= 0:
                effects.append(ParticleBurst([e.pos[0], e.pos[1], 100], size=50, count=30))
                enemies.remove(e)
        alive = []
        for p in projectiles:
            p.update(dt)
            if p.life <= 0 or p.pos[2] < -50:
                continue
            hit = False
            for wall in all_walls:
                if wall.intersects(p.pos) and p.pos[2] < wall.height:
                    effects.append(ParticleBurst(p.pos, size=80 if p.kind == 'ball' else 24, count=56 if p.kind == 'ball' else 18))
                    owner = wall.owner
                    if owner in wall_hp:
                        wall_hp[owner] = max(0, wall_hp[owner] - p.damage)
                    hit = True
                    break
            if not hit:
                alive.append(p)
        projectiles[:] = alive
        for ef in list(effects):
            ef.update(dt)
            if ef.life <= 0:
                effects.remove(ef)
    glutPostRedisplay()

def show_screen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, 1000, 800)
    setup_camera()
    glLightfv(GL_LIGHT0, GL_POSITION, lightPos)
    draw_multi_colored_grid()
    draw_all_structures()
    draw_mountain_range()
    draw_minimal_vegetation()
    for e in list(enemies):
        e.draw()
    for p in list(projectiles):
        p.draw()
    for ef in effects:
        ef.draw()
    for i in range(len(castle_configs)):
        draw_hp_bar_for_castle(i)
    draw_text(10, 770, f"Castle Complex with Perimeter Wall - {len(castle_configs)} Castles")
    draw_text(10, 740, "Controls: Arrows=Rotate, Z/X=Zoom, 1-4=Spawn Enemies, Space=Pause, T=Trails, F=Wireframe, P=Print Camera, Q=Quit")
    draw_text(10, 710, f"Camera Distance: {int(cam_dist)}")
    draw_text(10, 680, f"Enemies: {len(enemies)} | Wall HP: {wall_hp.get(DEFENDED_CASTLE_ID, 0)}")
    glutSwapBuffers()

def handle_special_keys(key, x, y):
    global cam_angle_h, cam_angle_v
    if key == GLUT_KEY_LEFT:
        cam_angle_h -= 5
    elif key == GLUT_KEY_RIGHT:
        cam_angle_h += 5
    elif key == GLUT_KEY_UP:
        cam_angle_v = min(89, cam_angle_v + 5)
    elif key == GLUT_KEY_DOWN:
        cam_angle_v = max(-10, cam_angle_v - 5)
    glutPostRedisplay()

def handle_keyboard(key, x, y):
    global cam_dist, pause, show_trails, wireframe
    if key == b'z':
        cam_dist = max(1000, cam_dist - 150)
    elif key == b'x':
        cam_dist = min(25000, cam_dist + 150)
    elif key == b' ':
        pause = not pause
    elif key == b't':
        show_trails = not show_trails
    elif key == b'f':
        wireframe = not wireframe
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE if wireframe else GL_FILL)
    elif key == b'1':
        spawn_enemy('barbarian')
    elif key == b'2':
        spawn_enemy('archer')
    elif key == b'3':
        spawn_enemy('giant')
    elif key == b'4':
        spawn_enemy('cannon')
    elif key == b'p':
        print(f"cam_angle_h={cam_angle_h}, cam_angle_v={cam_angle_v}, cam_dist={cam_dist}, enemies={len(enemies)}")
    elif key == b'q' or key == b'\x1b':
        sys.exit(0)
    glutPostRedisplay()

def main():
    global defended_cfg
    try:
        glutInit(sys.argv)
        print("GLUT initialized")
    except Exception as e:
        print(f"GLUT initialization failed: {e}")
        sys.exit(1)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"Castle Complex with Perimeter Wall")
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LESS)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (1.0, 1.0, 1.0, 1.0))
    glLightfv(GL_LIGHT0, GL_SPECULAR, (1.0, 1.0, 1.0, 1.0))
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT, GL_DIFFUSE)
    defended_cfg = castle_configs[DEFENDED_CASTLE_ID]
    for i in range(len(castle_configs)):
        wall_hp[i] = 1000
        wall_max[i] = 1000
    wall_hp['perimeter'] = 5000
    wall_max['perimeter'] = 5000
    init_walls()
    glutDisplayFunc(show_screen)
    glutIdleFunc(update)
    glutSpecialFunc(handle_special_keys)
    glutKeyboardFunc(handle_keyboard)
    glutMainLoop()

if __name__ == "__main__":
    main()




#====================================

# === ENEMY SECTION START ===
# This section defines the enemy classes and their spawning logic from gr.py.
# Enemies (Barbarian, Archer, Giant, Cannon) move toward castles or walls,
# attack when in range, and take damage from projectiles.

def vec_to(p1, p2):
    # Calculate vector from p1 to p2.
    return [p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]]

def norm(v):
    # Calculate the Euclidean norm of vector v.
    return sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])

class Enemy:
    # Base class for all enemies, handling movement, targeting, and attacking.
    def __init__(self, pos, speed=200.0, attack_range=140, attack_rate=1.4, damage=8):
        self.pos = [float(pos[0]), float(pos[1]), float(pos[2])]  # Initialize position as list of floats.
        self.speed = speed  # Set movement speed.
        self.state = 'advance'  # Set initial state to 'advance'.
        self.attack_cool = 0.0  # Initialize attack cooldown.
        self.hp = 100  # Set initial health.
        self.max_hp = 100  # Set maximum health.
        self.attacking = False  # Set attacking flag to False.
        self.target_wall = None  # Set target wall to None.
        self.attack_range = attack_range  # Set attack range.
        self.attack_rate = attack_rate  # Set attack rate.
        self.damage = damage  # Set damage per attack.

    def target_point(self):
        # Determine the closest target point (castle wall or perimeter wall).
        if self.attacking and self.target_wall:  # If attacking and has target.
            return self.target_wall.center  # Return target center.
        min_dist = float('inf')  # Initialize min distance.
        nearest_target = None  # Initialize nearest target.
        for i, cfg in enumerate(castle_configs):  # Loop through castles.
            x, y = cfg['position'][0], cfg['position'][1]  # Get castle position.
            size = cfg['size']  # Get size.
            wall_t = cfg['wall_thickness']  # Get wall thickness.
            half = size / 2.0 + wall_t / 2.0 + 100.0  # Calculate half size for targets.
            castle_targets = [  # Define targets on castle walls.
                [x, y - half, cfg['wall_height'] * 0.5],
                [x, y + half, cfg['wall_height'] * 0.5],
                [x - half, y, cfg['wall_height'] * 0.5],
                [x + half, y, cfg['wall_height'] * 0.5]
            ]
            for target in castle_targets:  # Loop through castle targets.
                dist = norm(vec_to(self.pos, target))  # Calculate distance.
                if dist < min_dist:  # If closer.
                    min_dist = dist  # Update min distance.
                    nearest_target = (target, i)  # Update nearest.
        for wall in all_walls:  # Loop through walls.
            dist = norm(vec_to(self.pos, wall.center))  # Calculate distance.
            if dist < min_dist:  # If closer.
                min_dist = dist  # Update min distance.
                nearest_target = (wall.center, wall.owner)  # Update nearest.
        if nearest_target:  # If target found.
            self.target_wall = None if isinstance(nearest_target[1], int) else nearest_target[1]  # Set target wall.
            return nearest_target[0]  # Return target position.
        cfg = defended_cfg  # Default to defended castle.
        x, y = cfg['position'][0], cfg['position'][1]  # Get position.
        size = cfg['size']  # Get size.
        wall_t = cfg['wall_thickness']  # Get wall thickness.
        half = size / 2.0 + wall_t / 2.0 + 100.0  # Calculate half size.
        return [x, y - half, cfg['wall_height'] * 0.5]  # Return default target.

    def update(self, dt):
        # Update enemy movement and attack logic.
        tp = self.target_point()  # Get target point.
        delta = vec_to(self.pos, tp)  # Get vector to target.
        d = norm(delta)  # Get distance to target.
        if not self.attacking:  # If not attacking.
            if d > self.attack_range:  # If outside range.
                dirx = delta[0] / d  # Normalize X direction.
                diry = delta[1] / d  # Normalize Y direction.
                step = self.speed * dt  # Calculate step size.
                new_x = self.pos[0] + dirx * step  # New X position.
                new_y = self.pos[1] + diry * step  # New Y position.
                intersect_wall = None  # Initialize wall intersection.
                for wall in all_walls:  # Check walls.
                    if wall.intersects([new_x, new_y, 0]):  # If intersects.
                        intersect_wall = wall  # Set intersected wall.
                        break  # Stop checking.
                if intersect_wall:  # If wall hit.
                    self.attacking = True  # Start attacking.
                    self.target_wall = intersect_wall  # Set target.
                    self.attack_cool = 0.0  # Reset cooldown.
                else:  # No hit.
                    self.pos[0] = new_x  # Update X.
                    self.pos[1] = new_y  # Update Y.
            else:  # Inside range.
                self.attacking = True  # Start attacking.
                self.attack_cool = 0.0  # Reset cooldown.
        else:  # Attacking.
            self.attack_cool -= dt  # Decrease cooldown.
            if self.attack_cool <= 0:  # If ready to attack.
                self.attack_cool = self.attack_rate  # Reset cooldown.
                owner = self.target_wall.owner if self.target_wall else DEFENDED_CASTLE_ID  # Get owner.
                if owner in wall_hp:  # If owner has HP.
                    wall_hp[owner] = max(0, wall_hp[owner] - self.damage)  # Deal damage.
                hit_pos = tp  # Set hit position.
                effects.append(ParticleBurst(hit_pos, size=40, count=28))  # Add particle effect.

    def draw_hp_bar(self):
        # Draw health bar above enemy, oriented toward camera.
        if self.hp <= 0:  # Skip if dead.
            return
        size = 60.0  # Bar size.
        pct = max(0.0, self.hp / self.max_hp)  # Health percentage.
        eye = get_camera_eye()  # Get camera position.
        dir_cam = [eye[0] - self.pos[0], eye[1] - self.pos[1], eye[2] - (self.pos[2] + 220)]  # Direction to camera.
        rx = -dir_cam[1]  # Right vector X.
        ry = dir_cam[0]  # Right vector Y.
        rz = 0.0  # Right vector Z.
        rlen = sqrt(max(1e-6, rx*rx + ry*ry))  # Right vector length.
        rx /= rlen  # Normalize right vector X.
        ry /= rlen  # Normalize right vector Y.
        ux = 0  # Up vector X.
        uy = 0  # Up vector Y.
        uz = 1.0  # Up vector Z.
        cx = self.pos[0]  # Center X.
        cy = self.pos[1]  # Center Y.
        cz = self.pos[2] + 330.0  # Center Z (above head).
        glDisable(GL_LIGHTING)  # Disable lighting for flat color.
        glColor3f(0.15, 0.15, 0.15)  # Gray background.
        glBegin(GL_QUADS)  # Draw background quad.
        glVertex3f(cx - rx*size - ux*6, cy - ry*size - uy*6, cz - uz*6)
        glVertex3f(cx + rx*size - ux*6, cy + ry*size - uy*6, cz - uz*6)
        glVertex3f(cx + rx*size + ux*6, cy + ry*size + uy*6, cz + uz*6)
        glVertex3f(cx - rx*size + ux*6, cy - ry*size + uy*6, cz + uz*6)
        glEnd()
        glColor3f(1.0 - pct, pct, 0.1)  # Health color (red to green).
        glBegin(GL_QUADS)  # Draw health quad.
        hw = size * 0.98 * pct  # Health width.
        glVertex3f(cx - rx*size, cy - ry*size, cz)
        glVertex3f(cx - rx*size + rx*hw, cy - ry*size + ry*hw, cz)
        glVertex3f(cx - rx*size + rx*hw + ux*6, cy - ry*size + ry*hw + uy*6, cz + uz*6)
        glVertex3f(cx - rx*size + ux*6, cy - ry*size + uy*6, cz + uz*6)
        glEnd()
        glEnable(GL_LIGHTING)  # Re-enable lighting.

class Barbarian(Enemy):
    # Barbarian enemy with melee attack and hammer swing animation.
    def __init__(self, pos):
        super().__init__(pos, speed=260.0, attack_range=140, attack_rate=1.4, damage=8)  # Initialize with specific stats.
        self.swing_phase = 0.0  # Initialize swing animation phase.
        self.hp = 90  # Set health.
        self.max_hp = 90  # Set max health.

    def update(self, dt):
        super().update(dt)  # Call base update.
        if self.attacking:  # If attacking.
            self.swing_phase += dt * 6.0  # Update swing animation.

    def draw(self):
        # Draw barbarian with animated hammer swing.
        glPushMatrix()  # Save matrix.
        glTranslatef(self.pos[0], self.pos[1], 0)  # Move to position.
        set_material((0.8, 0.6, 0.5))  # Realistic skin color for legs.
        glPushMatrix()  # Save for left leg.
        glTranslatef(-18, 0, 70)  # Position left leg.
        draw_box(20, 20, 140)  # Draw left leg.
        glPopMatrix()
        glPushMatrix()  # Save for right leg.
        glTranslatef(18, 0, 70)  # Position right leg.
        draw_box(20, 20, 140)  # Draw right leg.
        glPopMatrix()
        set_material((0.4, 0.3, 0.2))  # Brown fur/leather for body.
        glPushMatrix()  # Save for body.
        glTranslatef(0, 0, 170)  # Position body.
        draw_box(80, 40, 140)  # Draw body.
        glPopMatrix()
        set_material((0.8, 0.6, 0.5))  # Skin for head.
        glPushMatrix()  # Save for head.
        glTranslatef(0, 0, 260)  # Position head.
        draw_sphere(28)  # Draw head.
        glPopMatrix()
        set_material((0.8, 0.6, 0.5))  # Skin for arms.
        glPushMatrix()  # Save for left arm.
        glTranslatef(40, 0, 190)  # Position left arm.
        draw_box(20, 20, 100)  # Draw left arm.
        glPopMatrix()
        glPushMatrix()  # Save for right arm with hammer.
        glTranslatef(-40, 0, 190)  # Position right arm.
        glRotatef(45 * sin(self.swing_phase), 1, 0, 0)  # Animate swing.
        draw_box(20, 20, 100)  # Draw right arm.
        glPopMatrix()
        glPushMatrix()  # Save for hammer.
        glTranslatef(50, 0, 220)  # Position hammer.
        glRotatef(-70 + 60 * sin(self.swing_phase), 1, 0, 0)  # Animate hammer swing.
        set_material((0.5, 0.5, 0.5))  # Gray metal for hammer.
        draw_cylinder(10, 100)  # Draw hammer handle.
        glTranslatef(0, 0, 100)  # Move to hammer head.
        draw_box(30, 50, 30)  # Draw hammer head.
        glPopMatrix()
        glPopMatrix()  # Restore matrix.
        self.draw_hp_bar()  # Draw health bar.

class Giant(Enemy):
    # Giant enemy with slow, powerful melee attacks.
    def __init__(self, pos):
        super().__init__(pos, speed=150.0, attack_range=300, attack_rate=2.0, damage=22)  # Initialize with specific stats.
        self.swing = 0.0  # Initialize swing animation.
        self.hp = 260  # Set health.
        self.max_hp = 260  # Set max health.

    def update(self, dt):
        super().update(dt)  # Call base update.
        if self.attacking:  # If attacking.
            self.swing += dt * 2.0  # Update swing animation.

    def draw(self):
        # Draw giant with animated arm swings.
        scale = 2.0  # Scale factor for size.
        glPushMatrix()  # Save matrix.
        glTranslatef(self.pos[0], self.pos[1], 0)  # Move to position.
        glScalef(scale, scale, scale)  # Apply scale.
        set_material((0.6, 0.5, 0.4))  # Grayish skin for legs.
        glPushMatrix()  # Save for left leg.
        glTranslatef(-20, 0, 80)  # Position left leg.
        draw_box(26, 26, 160)  # Draw left leg.
        glPopMatrix()
        glPushMatrix()  # Save for right leg.
        glTranslatef(20, 0, 80)  # Position right leg.
        draw_box(26, 26, 160)  # Draw right leg.
        glPopMatrix()
        set_material((0.3, 0.2, 0.15))  # Dark leather for body.
        glPushMatrix()  # Save for body.
        glTranslatef(0, 0, 200)  # Position body.
        draw_box(110, 50, 180)  # Draw body.
        glPopMatrix()
        set_material((0.6, 0.5, 0.4))  # Skin for head.
        glPushMatrix()  # Save for head.
        glTranslatef(0, 0, 300)  # Position head.
        draw_sphere(36)  # Draw head.
        glPopMatrix()
        set_material((0.6, 0.5, 0.4))  # Skin for arms.
        glPushMatrix()  # Save for left arm.
        glTranslatef(-70, 0, 220)  # Position left arm.
        glRotatef(30 * sin(self.swing), 1, 0, 0)  # Animate swing.
        draw_box(26, 26, 140)  # Draw left arm.
        glPopMatrix()
        glPushMatrix()  # Save for right arm.
        glTranslatef(70, 0, 220)  # Position right arm.
        glRotatef(-30 * sin(self.swing), 1, 0, 0)  # Animate swing.
        draw_box(26, 26, 140)  # Draw right arm.
        glPopMatrix()
        glPopMatrix()  # Restore matrix.
        self.draw_hp_bar()  # Draw health bar.

class Archer(Enemy):
    # Archer enemy with ranged arrow attacks.
    def __init__(self, pos):
        super().__init__(pos, speed=240.0, attack_range=1200, attack_rate=random.uniform(1.0, 1.8), damage=6)  # Initialize with specific stats.
        self.reload = random.uniform(1.2, 2.0)  # Initialize reload timer.
        self.hp = 70  # Set health.
        self.max_hp = 70  # Set max health.

    def update(self, dt):
        super().update(dt)  # Call base update.
        if self.attacking:  # If attacking.
            self.reload -= dt  # Decrease reload timer.
            if self.reload <= 0:  # If ready to shoot.
                self.reload = self.attack_rate  # Reset reload.
                tp = self.target_point()  # Get target point.
                delta = vec_to(self.pos, tp)  # Get vector to target.
                d = norm(delta)  # Get distance.
                dirx, diry, dirz = delta[0]/d, delta[1]/d, delta[2]/d  # Normalize direction.
                speed = 900.0  # Arrow speed.
                proj_vel = [dirx * speed, diry * speed, dirz * speed + 180.0]  # Calculate velocity.
                projectiles.append(Projectile([self.pos[0], self.pos[1], 160.0], proj_vel, radius=6.0, kind='arrow', damage=self.damage))  # Spawn arrow.

    def draw(self):
        # Draw archer with bow.
        glPushMatrix()  # Save matrix.
        glTranslatef(self.pos[0], self.pos[1], 0)  # Move to position.
        set_material((0.3, 0.4, 0.2))  # Green tunic for legs.
        glPushMatrix()  # Save for left leg.
        glTranslatef(-12, 0, 60)  # Position left leg.
        draw_box(16, 16, 120)  # Draw left leg.
        glPopMatrix()
        glPushMatrix()  # Save for right leg.
        glTranslatef(12, 0, 60)  # Position right leg.
        draw_box(16, 16, 120)  # Draw right leg.
        glPopMatrix()
        set_material((0.25, 0.35, 0.15))  # Dark green for body.
        glPushMatrix()  # Save for body.
        glTranslatef(0, 0, 150)  # Position body.
        draw_box(60, 30, 120)  # Draw body.
        glPopMatrix()
        set_material((0.9, 0.7, 0.6))  # Skin for head.
        glPushMatrix()  # Save for head.
        glTranslatef(0, 0, 220)  # Position head.
        draw_sphere(22)  # Draw head.
        glPopMatrix()
        set_material((0.5, 0.3, 0.1))  # Brown for bow.
        glPushMatrix()  # Save for bow.
        glTranslatef(40, 0, 160)  # Position bow.
        glRotatef(90, 0, 1, 0)  # Rotate bow.
        draw_cylinder(3, 60)  # Draw bow.
        glPopMatrix()
        glPopMatrix()  # Restore matrix.
        self.draw_hp_bar()  # Draw health bar.

class Cannon(Enemy):
    # Cannon enemy with long-range, high-damage attacks.
    def __init__(self, pos):
        super().__init__(pos, speed=160.0, attack_range=2200, attack_rate=random.uniform(2.0, 3.0), damage=30)  # Initialize with specific stats.
        self.reload = random.uniform(2.2, 3.4)  # Initialize reload timer.
        self.hp = 120  # Set health.
        self.max_hp = 120  # Set max health.

    def update(self, dt):
        super().update(dt)  # Call base update.
        if self.attacking:  # If attacking.
            self.reload -= dt  # Decrease reload timer.
            if self.reload <= 0:  # If ready to fire.
                self.reload = self.attack_rate  # Reset reload.
                tp = self.target_point()  # Get target point.
                delta = vec_to(self.pos, tp)  # Get vector to target.
                d = norm(delta)  # Get distance.
                dirx, diry, dirz = delta[0]/d, delta[1]/d, delta[2]/d  # Normalize direction.
                v0 = 1100.0  # Cannonball speed.
                projectiles.append(Projectile([self.pos[0], self.pos[1], 120.0], [dirx * v0, diry * v0, dirz * v0 + 200.0], radius=30.0, kind='ball', damage=self.damage))  # Spawn cannonball.

    def draw(self):
        # Draw cannon with wheels and barrel.
        glPushMatrix()  # Save matrix.
        glTranslatef(self.pos[0], self.pos[1], 0)  # Move to position.
        set_material((0.2, 0.2, 0.2))  # Dark metal for wheels.
        for sx in (-40, 40):  # Draw wheels.
            glPushMatrix()  # Save for left wheel.
            glTranslatef(sx, -24, 36)  # Position left wheel.
            glRotatef(90, 0, 1, 0)  # Rotate wheel.
            draw_cylinder(22, 12)  # Draw left wheel.
            glPopMatrix()
            glPushMatrix()  # Save for right wheel.
            glTranslatef(sx, 24, 36)  # Position right wheel.
            glRotatef(90, 0, 1, 0)  # Rotate wheel.
            draw_cylinder(22, 12)  # Draw right wheel.
            glPopMatrix()
        set_material((0.4, 0.25, 0.1))  # Brown wood for base.
        glPushMatrix()  # Save for base.
        glTranslatef(0, 0, 40)  # Position base.
        draw_box(160, 80, 40)  # Draw base.
        glPopMatrix()
        set_material((0.2, 0.2, 0.2))  # Metal for cannon barrel.
        glPushMatrix()  # Save for barrel.
        glTranslatef(0, 0, 90)  # Position barrel.
        glRotatef(10, 1, 0, 0)  # Tilt barrel.
        draw_cylinder(20, 140)  # Draw barrel.
        glPopMatrix()
        glPopMatrix()  # Restore matrix.
        self.draw_hp_bar()  # Draw health bar.

SPAWN_RADIUS = 7000.0
spawn_timers = {'barbarian': 0.0, 'archer': 0.0, 'giant': 0.0, 'cannon': 0.0}
spawn_flags = {'barbarian': True, 'archer': True, 'giant': True, 'cannon': True}

def rand_spawn_pos():
    # Generate random spawn position on a circle.
    a = random.uniform(0, 2 * pi)
    return [cos(a) * SPAWN_RADIUS, sin(a) * SPAWN_RADIUS, 0.0]

def spawn_enemy(kind):
    # Spawn an enemy of the specified kind.
    pos = rand_spawn_pos()  # Get spawn position.
    if kind == 'barbarian':
        enemies.append(Barbarian(pos))  # Spawn barbarian.
    elif kind == 'archer':
        enemies.append(Archer(pos))  # Spawn archer.
    elif kind == 'giant':
        enemies.append(Giant(pos))  # Spawn giant.
    elif kind == 'cannon':
        enemies.append(Cannon(pos))  # Spawn cannon.

def update_spawning(dt):
    # Update spawning timers and spawn enemies when ready.
    spawn_timers['barbarian'] -= dt  # Decrease barbarian timer.
    if spawn_flags['barbarian'] and spawn_timers['barbarian'] <= 0:  # If ready.
        spawn_timers['barbarian'] = random.uniform(1.0, 2.5)  # Reset timer.
        enemies.append(Barbarian(rand_spawn_pos()))  # Spawn barbarian.
    spawn_timers['archer'] -= dt  # Decrease archer timer.
    if spawn_flags['archer'] and spawn_timers['archer'] <= 0:  # If ready.
        spawn_timers['archer'] = random.uniform(2.2, 3.5)  # Reset timer.
        enemies.append(Archer(rand_spawn_pos()))  # Spawn archer.
    spawn_timers['giant'] -= dt  # Decrease giant timer.
    if spawn_flags['giant'] and spawn_timers['giant'] <= 0:  # If ready.
        spawn_timers['giant'] = random.uniform(4.0, 7.0)  # Reset timer.
        enemies.append(Giant(rand_spawn_pos()))  # Spawn giant.
    spawn_timers['cannon'] -= dt  # Decrease cannon timer.
    if spawn_flags['cannon'] and spawn_timers['cannon'] <= 0:  # If ready.
        spawn_timers['cannon'] = random.uniform(5.0, 8.0)  # Reset timer.
        enemies.append(Cannon(rand_spawn_pos()))  # Spawn cannon.

# === ENEMY SECTION END ===

def get_camera_eye():
    th = radians(cam_angle_h)
    ph = radians(cam_angle_v)
    cx = cos(th) * cos(ph) * cam_dist
    cy = sin(th) * cos(ph) * cam_dist
    cz = sin(ph) * cam_dist
    target = [defended_cfg['position'][0], defended_cfg['position'][1], defended_cfg['wall_height']]
    return [cx + target[0], cy + target[1], cz + target[2]]

def draw_hp_bar_for_castle(cfg_id):
    if cfg_id not in wall_hp:
        return
    cfg = castle_configs[cfg_id]
    cx, cy, _ = cfg['position']
    posx = cx
    posy = cy
    posz = cfg['height'] + cfg['wall_height'] + 180.0
    hp = wall_hp[cfg_id]
    hpmax = wall_max[cfg_id]
    pct = hp / float(hpmax) if hpmax > 0 else 0.0
    glDisable(GL_LIGHTING)
    glColor3f(0.15, 0.15, 0.15)
    glBegin(GL_QUADS)
    glVertex3f(posx - 150, posy, posz)
    glVertex3f(posx + 150, posy, posz)
    glVertex3f(posx + 150, posy, posz + 16)
    glVertex3f(posx - 150, posy, posz + 16)
    glEnd()
    glColor3f(1.0 - pct, pct, 0.1)
    glBegin(GL_QUADS)
    glVertex3f(posx - 148, posy + 0.1, posz + 2)
    glVertex3f(posx - 148 + 296 * pct, posy + 0.1, posz + 2)
    glVertex3f(posx - 148 + 296 * pct, posy + 0.1, posz + 14)
    glVertex3f(posx - 148, posy + 0.1, posz + 14)
    glEnd()
    glEnable(GL_LIGHTING)
#====================================



#============
#new
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from math import sin, cos, atan2, radians, sqrt, pi
import random
import time

# Global variables
GRID_LENGTH = 500
cam_angle_h = 45
cam_angle_v = 30
cam_dist = 4000
fovY = 60

# Castle configurations
castle_configs = [
    {
        'position': [-800, -1600, 0],
        'size': 1600,
        'height': 800,
        'roof_z': 600,
        'tower_radius': 160,
        'floors': 7,
        'wall_thickness': 300,
        'wall_height': 600,
        'color_scheme': 'reddish'
    },
    {
        'position': [900, 1000, 0],
        'size': 1600,
        'height': 1200,
        'roof_z': 800,
        'tower_radius': 180,
        'floors': 12,
        'wall_thickness': 400,
        'wall_height': 800,
        'color_scheme': 'reddish'
    },
    {
        'position': [-3300, 400, 0],
        'size': 2000,
        'height': 600,
        'roof_z': 450,
        'tower_radius': 120,
        'floors': 3,
        'wall_thickness': 300,
        'wall_height': 450,
        'color_scheme': 'reddish'
    }
]

# Central rock tower position
central_rock_pos = [-1000, 1500, 0]
player_pos = [central_rock_pos[0], central_rock_pos[1], central_rock_pos[2] + 1630]
player_speed = 50
player_angle = 0
player_turn_speed = 5
teleport_skip_clamp = False

# Enemy system variables
enemies = []
projectiles = []
effects = []
castle_hp = {0: 6000, 1: 8000, 2: 4500}
castle_max_hp = {0: 6000, 1: 8000, 2: 4500}
last_spawn_time = 0
spawn_interval = 3.0
game_time = 0

# Wall collision system
class Wall:
    def __init__(self, x1, y1, x2, y2, height, owner_id):
        self.x1, self.y1 = x1, y1
        self.x2, self.y2 = x2, y2
        self.center_x = (x1 + x2) / 2
        self.center_y = (y1 + y2) / 2
        self.height = height
        self.owner_id = owner_id
        self.hp = height * 2  # Wall HP based on height
        self.max_hp = self.hp
        
    def distance_to_point(self, px, py):
        # Calculate distance from point to line segment
        A = px - self.x1
        B = py - self.y1
        C = self.x2 - self.x1
        D = self.y2 - self.y1
        
        dot = A * C + B * D
        len_sq = C * C + D * D
        
        if len_sq == 0:
            return sqrt(A * A + B * B)
            
        param = dot / len_sq
        
        if param < 0:
            xx, yy = self.x1, self.y1
        elif param > 1:
            xx, yy = self.x2, self.y2
        else:
            xx = self.x1 + param * C
            yy = self.y1 + param * D
            
        dx = px - xx
        dy = py - yy
        return sqrt(dx * dx + dy * dy)
    
    def check_line_collision(self, x1, y1, x2, y2, enemy_radius=50):
        """Check if a line from (x1,y1) to (x2,y2) collides with this wall"""
        # Check if line intersects with wall line segment
        # Using line-line intersection with thickness consideration
        
        # Wall vector
        wx = self.x2 - self.x1
        wy = self.y2 - self.y1
        
        # Movement vector
        mx = x2 - x1
        my = y2 - y1
        
        # Vector from wall start to movement start
        sx = x1 - self.x1
        sy = y1 - self.y1
        
        # Calculate intersection using cross products
        cross1 = wx * my - wy * mx
        if abs(cross1) < 1e-10:  # Lines are parallel
            # Check if the movement line is close to wall
            dist_start = self.distance_to_point(x1, y1)
            dist_end = self.distance_to_point(x2, y2)
            return min(dist_start, dist_end) < enemy_radius
        
        cross2 = sx * my - sy * mx
        cross3 = sx * wy - sy * wx
        
        t = cross2 / cross1  # Parameter for wall line
        u = cross3 / cross1  # Parameter for movement line
        
        # Check if intersection is within both line segments
        if 0 <= t <= 1 and 0 <= u <= 1:
            # Calculate intersection point
            ix = self.x1 + t * wx
            iy = self.y1 + t * wy
            
            # Check if intersection is close enough considering enemy radius
            dist_to_intersection = sqrt((ix - x2)**2 + (iy - y2)**2)
            return dist_to_intersection < enemy_radius
        
        # No intersection within line segments, check distance to endpoints
        return self.distance_to_point(x2, y2) < enemy_radius

# Create walls for each castle
castle_walls = []
for i, config in enumerate(castle_configs):
    pos = config['position']
    size = config['size']
    wall_height = config['wall_height']
    half_size = size / 2
    
    # Four walls around each castle
    walls = [
        Wall(pos[0] - half_size, pos[1] - half_size, pos[0] + half_size, pos[1] - half_size, wall_height, i),  # South
        Wall(pos[0] + half_size, pos[1] - half_size, pos[0] + half_size, pos[1] + half_size, wall_height, i),  # East
        Wall(pos[0] + half_size, pos[1] + half_size, pos[0] - half_size, pos[1] + half_size, wall_height, i),  # North
        Wall(pos[0] - half_size, pos[1] + half_size, pos[0] - half_size, pos[1] - half_size, wall_height, i),  # West
    ]
    castle_walls.extend(walls)

# Enemy Classes
class Enemy:
    def __init__(self, pos, target_castle_id, speed=100, hp=100, damage=10, attack_range=150):
        self.pos = [float(pos[0]), float(pos[1]), float(pos[2])]
        self.target_castle_id = target_castle_id
        self.speed = speed
        self.hp = hp
        self.max_hp = hp
        self.damage = damage
        self.attack_range = attack_range
        self.attacking = False
        self.attack_cooldown = 0.0
        self.attack_rate = 1.0
        self.target_wall = None
        
    def find_nearest_wall(self):
        """Find the nearest wall belonging to target castle"""
        nearest_wall = None
        min_distance = float('inf')
        
        for wall in castle_walls:
            if wall.owner_id == self.target_castle_id and wall.hp > 0:
                dist = wall.distance_to_point(self.pos[0], self.pos[1])
                if dist < min_distance:
                    min_distance = dist
                    nearest_wall = wall
                    
        return nearest_wall, min_distance
    
    def get_target_position(self):
        """Get position of target (wall center or castle center)"""
        if self.target_wall and self.target_wall.hp > 0:
            return [self.target_wall.center_x, self.target_wall.center_y, 0]
        else:
            castle = castle_configs[self.target_castle_id]
            return castle['position']
    
    def update(self, dt):
        """Update enemy position and attack logic"""
        # First, check if we should target a wall
        if not self.target_wall or self.target_wall.hp <= 0:
            wall, wall_distance = self.find_nearest_wall()
            if wall and wall_distance < 300:  # Switch to wall target if close
                self.target_wall = wall
        
        target_pos = self.get_target_position()
        dx = target_pos[0] - self.pos[0]
        dy = target_pos[1] - self.pos[1]
        distance = sqrt(dx*dx + dy*dy)
        
        if distance > self.attack_range:
            # Move towards target
            if distance > 0:
                self.pos[0] += (dx / distance) * self.speed * dt
                self.pos[1] += (dy / distance) * self.speed * dt
            self.attacking = False
        else:
            # In range - attack
            self.attacking = True
            self.attack_cooldown -= dt
            if self.attack_cooldown <= 0:
                self.attack()
                self.attack_cooldown = self.attack_rate
    
    def attack(self):
        """Attack the wall or castle"""
        global castle_hp
        
        if self.target_wall and self.target_wall.hp > 0:
            # Attack wall
            self.target_wall.hp -= self.damage
            effects.append(ExplosionEffect([self.target_wall.center_x, self.target_wall.center_y, 100]))
            if self.target_wall.hp <= 0:
                self.target_wall = None  # Wall destroyed, target castle
        else:
            # Attack castle directly
            if self.target_castle_id in castle_hp:
                castle_hp[self.target_castle_id] = max(0, castle_hp[self.target_castle_id] - self.damage)
                target_pos = self.get_target_position()
                effects.append(ExplosionEffect(target_pos))
    
    def take_damage(self, damage):
        """Take damage from player"""
        self.hp -= damage
        return self.hp <= 0
    
    def draw_hp_bar(self):
        """Draw health bar above enemy"""
        if self.hp <= 0:
            return
        
        bar_width = 80
        bar_height = 8
        hp_percent = self.hp / self.max_hp
        
        glPushAttrib(GL_ENABLE_BIT | GL_CURRENT_BIT)
        glDisable(GL_LIGHTING)
        
        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], self.pos[2] + 150)
        
        # Background
        glColor3f(0.8, 0.2, 0.2)
        glBegin(GL_QUADS)
        glVertex3f(-bar_width/2, -bar_height/2, 0)
        glVertex3f(bar_width/2, -bar_height/2, 0)
        glVertex3f(bar_width/2, bar_height/2, 0)
        glVertex3f(-bar_width/2, bar_height/2, 0)
        glEnd()
        
        # Health
        glColor3f(0.2, 0.8, 0.2)
        hp_width = bar_width * hp_percent
        glBegin(GL_QUADS)
        glVertex3f(-bar_width/2, -bar_height/2, 1)
        glVertex3f(-bar_width/2 + hp_width, -bar_height/2, 1)
        glVertex3f(-bar_width/2 + hp_width, bar_height/2, 1)
        glVertex3f(-bar_width/2, bar_height/2, 1)
        glEnd()
        
        glPopMatrix()
        glPopAttrib()

class Barbarian(Enemy):
    def __init__(self, pos, target_castle_id):
        super().__init__(pos, target_castle_id, speed=120, hp=150, damage=15, attack_range=120)
        self.swing_animation = 0
    
    def update(self, dt):
        super().update(dt)
        if self.attacking:
            self.swing_animation += dt * 8
    
    def draw(self):
        quad = gluNewQuadric()
        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], self.pos[2])
        
        # Body (brown)
        glColor3f(0.6, 0.4, 0.2)
        draw_cube_manual_shading(0, 0, 80, 40, 30, 120, [0.6, 0.4, 0.2])
        
        # Head
        glPushMatrix()
        glTranslatef(0, 0, 160)
        glColor3f(0.8, 0.6, 0.5)
        gluSphere(quad, 25, 12, 12)
        glPopMatrix()
        
        # Hammer with swing animation
        glPushMatrix()
        glTranslatef(40, 0, 120)
        if self.attacking:
            glRotatef(30 * sin(self.swing_animation), 1, 0, 0)
        glColor3f(0.4, 0.2, 0.1)
        gluCylinder(quad, 5, 5, 60, 8, 8)
        glTranslatef(0, 0, 60)
        glColor3f(0.7, 0.7, 0.7)
        draw_cube_manual_shading(0, 0, 0, 25, 25, 15, [0.7, 0.7, 0.7])
        glPopMatrix()
        
        glPopMatrix()
        self.draw_hp_bar()

class Archer(Enemy):
    def __init__(self, pos, target_castle_id):
        super().__init__(pos, target_castle_id, speed=100, hp=80, damage=8, attack_range=800)
        self.attack_rate = 1.5
    
    def attack(self):
        """Shoot arrow at target"""
        target_pos = self.get_target_position()
        dx = target_pos[0] - self.pos[0]
        dy = target_pos[1] - self.pos[1]
        dz = target_pos[2] + 200 - self.pos[2]
        distance = sqrt(dx*dx + dy*dy + dz*dz)
        
        if distance > 0:
            speed = 500
            vel = [dx/distance * speed, dy/distance * speed, dz/distance * speed]
            projectiles.append(Arrow(self.pos[:], vel, self.damage, self.target_castle_id, self.target_wall))
    
    def draw(self):
        quad = gluNewQuadric()
        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], self.pos[2])
        
        # Body (green)
        glColor3f(0.2, 0.6, 0.2)
        draw_cube_manual_shading(0, 0, 70, 35, 25, 100, [0.2, 0.6, 0.2])
        
        # Head
        glPushMatrix()
        glTranslatef(0, 0, 130)
        glColor3f(0.8, 0.6, 0.5)
        gluSphere(quad, 20, 12, 12)
        glPopMatrix()
        
        # Bow
        glPushMatrix()
        glTranslatef(30, 0, 90)
        glRotatef(90, 0, 1, 0)
        glColor3f(0.6, 0.3, 0.1)
        gluCylinder(quad, 3, 3, 50, 8, 8)
        glPopMatrix()
        
        glPopMatrix()
        self.draw_hp_bar()

class Giant(Enemy):
    def __init__(self, pos, target_castle_id):
        super().__init__(pos, target_castle_id, speed=60, hp=300, damage=25, attack_range=200)
        self.attack_rate = 2.0
        self.scale = 1.5
    
    def draw(self):
        quad = gluNewQuadric()
        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], self.pos[2])
        glScalef(self.scale, self.scale, self.scale)
        
        # Body (dark gray)
        glColor3f(0.4, 0.4, 0.4)
        draw_cube_manual_shading(0, 0, 100, 60, 40, 160, [0.4, 0.4, 0.4])
        
        # Head
        glPushMatrix()
        glTranslatef(0, 0, 200)
        glColor3f(0.5, 0.5, 0.5)
        gluSphere(quad, 40, 12, 12)
        glPopMatrix()
        
        # Arms
        for x_offset in [-50, 50]:
            glPushMatrix()
            glTranslatef(x_offset, 0, 150)
            glColor3f(0.4, 0.4, 0.4)
            gluCylinder(quad, 15, 15, 80, 8, 8)
            glPopMatrix()
        
        glPopMatrix()
        self.draw_hp_bar()

class Arrow:
    def __init__(self, pos, vel, damage, target_castle_id, target_wall=None):
        self.pos = pos[:]
        self.vel = vel[:]
        self.damage = damage
        self.target_castle_id = target_castle_id
        self.target_wall = target_wall
        self.life = 3.0
    
    def update(self, dt):
        """Update arrow position"""
        self.pos[0] += self.vel[0] * dt
        self.pos[1] += self.vel[1] * dt
        self.pos[2] += self.vel[2] * dt
        self.vel[2] -= 300 * dt
        self.life -= dt
        
        # Check collision
        if self.target_wall and self.target_wall.hp > 0:
            if self.target_wall.distance_to_point(self.pos[0], self.pos[1]) < 50 and self.pos[2] < 200:
                self.target_wall.hp -= self.damage
                effects.append(ExplosionEffect(self.pos[:]))
                return True
        else:
            # Check castle collision
            target_pos = castle_configs[self.target_castle_id]['position']
            castle_size = castle_configs[self.target_castle_id]['size']
            
            dx = self.pos[0] - target_pos[0]
            dy = self.pos[1] - target_pos[1]
            
            if (abs(dx) < castle_size/2 and abs(dy) < castle_size/2 and 
                self.pos[2] > target_pos[2] and self.pos[2] < target_pos[2] + 600):
                global castle_hp
                if self.target_castle_id in castle_hp:
                    castle_hp[self.target_castle_id] = max(0, castle_hp[self.target_castle_id] - self.damage)
                effects.append(ExplosionEffect(self.pos[:]))
                return True
        
        return self.life <= 0 or self.pos[2] < 0
    
    def draw(self):
        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], self.pos[2])
        glColor3f(0.6, 0.3, 0.1)
        quad = gluNewQuadric()
        gluCylinder(quad, 2, 2, 20, 6, 6)
        glPopMatrix()

class ExplosionEffect:
    def __init__(self, pos):
        self.pos = pos[:]
        self.life = 1.0
        self.max_life = 1.0
        self.particles = []
        for _ in range(20):
            angle = random.uniform(0, 2*pi)
            speed = random.uniform(50, 150)
            self.particles.append({
                'pos': pos[:],
                'vel': [cos(angle)*speed, sin(angle)*speed, random.uniform(50, 200)]
            })
    
    def update(self, dt):
        self.life -= dt
        for particle in self.particles:
            particle['pos'][0] += particle['vel'][0] * dt
            particle['pos'][1] += particle['vel'][1] * dt
            particle['pos'][2] += particle['vel'][2] * dt
            particle['vel'][2] -= 500 * dt
        return self.life <= 0
    
    def draw(self):
        glPushAttrib(GL_ENABLE_BIT | GL_CURRENT_BIT)
        glDisable(GL_LIGHTING)
        glPointSize(5.0)
        glBegin(GL_POINTS)
        intensity = self.life / self.max_life
        glColor3f(1.0 * intensity, 0.5 * intensity, 0.0)
        for particle in self.particles:
            if particle['pos'][2] > 0:
                glVertex3f(particle['pos'][0], particle['pos'][1], particle['pos'][2])
        glEnd()
        glPointSize(1.0)
        glPopAttrib()

def spawn_enemy():
    """Spawn random enemy targeting random castle"""
    angle = random.uniform(0, 2*pi)
    distance = 3000
    spawn_x = distance * cos(angle)
    spawn_y = distance * sin(angle)
    spawn_pos = [spawn_x, spawn_y, 0]
    
    target_castle_id = random.choice([0, 2])  # Target castle 1 or 3
    enemy_type = random.choice(['barbarian', 'archer', 'giant'])
    
    if enemy_type == 'barbarian':
        enemies.append(Barbarian(spawn_pos, target_castle_id))
    elif enemy_type == 'archer':
        enemies.append(Archer(spawn_pos, target_castle_id))
    elif enemy_type == 'giant':
        enemies.append(Giant(spawn_pos, target_castle_id))

def update_enemies(dt):
    """Update all enemies and projectiles"""
    global enemies, projectiles, effects
    
    enemies_to_remove = []
    for enemy in enemies:
        enemy.update(dt)
        if enemy.hp <= 0:
            enemies_to_remove.append(enemy)
    
    for enemy in enemies_to_remove:
        enemies.remove(enemy)
    
    projectiles_to_remove = []
    for projectile in projectiles:
        if projectile.update(dt):
            projectiles_to_remove.append(projectile)
    
    for projectile in projectiles_to_remove:
        projectiles.remove(projectile)
    
    effects_to_remove = []
    for effect in effects:
        if effect.update(dt):
            effects_to_remove.append(effect)
    
    for effect in effects_to_remove:
        effects.remove(effect)

def draw_enemies():
    """Draw all enemies, projectiles, and effects"""
    for enemy in enemies:
        enemy.draw()
    
    for projectile in projectiles:
        projectile.draw()
    
    for effect in effects:
        effect.draw()

def draw_castle_hp_bars():
    """Draw HP bars for each castle"""
    glPushAttrib(GL_ENABLE_BIT | GL_CURRENT_BIT)
    glDisable(GL_LIGHTING)
    
    for i, castle in enumerate(castle_configs):
        if i not in castle_hp:
            continue
            
        pos = castle['position']
        hp = castle_hp[i]
        max_hp = castle_max_hp[i]
        hp_percent = hp / max_hp
        
        bar_x = pos[0]
        bar_y = pos[1]
        bar_z = pos[2] + castle['height'] + 300
        bar_width = 200
        bar_height = 20
        
        glPushMatrix()
        glTranslatef(bar_x, bar_y, bar_z)
        
        # Background
        glColor3f(0.8, 0.2, 0.2)
        glBegin(GL_QUADS)
        glVertex3f(-bar_width/2, -bar_height/2, 0)
        glVertex3f(bar_width/2, -bar_height/2, 0)
        glVertex3f(bar_width/2, bar_height/2, 0)
        glVertex3f(-bar_width/2, bar_height/2, 0)
        glEnd()
        
        # Health
        if hp_percent > 0.6:
            glColor3f(0.2, 0.8, 0.2)
        elif hp_percent > 0.3:
            glColor3f(0.8, 0.8, 0.2)
        else:
            glColor3f(0.8, 0.2, 0.2)
            
        hp_width = bar_width * hp_percent
        glBegin(GL_QUADS)
        glVertex3f(-bar_width/2, -bar_height/2, 1)
        glVertex3f(-bar_width/2 + hp_width, -bar_height/2, 1)
        glVertex3f(-bar_width/2 + hp_width, bar_height/2, 1)
        glVertex3f(-bar_width/2, bar_height/2, 1)
        glEnd()
        
        glPopMatrix()
    
    glPopAttrib()

def get_color_scheme(scheme_name, base_color):
    """Get color based on scheme"""
    if scheme_name == 'reddish':
        return [min(1.0, base_color[0] * 1.2), base_color[1] * 0.8, base_color[2] * 0.8]
    else:
        return base_color

def draw_cube_manual_shading(x, y, z, dx, dy, dz, base_color):
    """Draw cube with manual face shading"""
    glPushMatrix()
    glTranslatef(x, y, z)
    
    top_color = [min(1.0, c * 1.3) for c in base_color]
    front_color = base_color
    side_color = [c * 0.7 for c in base_color]
    back_color = [c * 0.5 for c in base_color]
    
    glBegin(GL_QUADS)
    # Top face
    glColor3f(top_color[0], top_color[1], top_color[2])
    glVertex3f(-dx/2, dy/2, -dz/2)
    glVertex3f(-dx/2, dy/2, dz/2)
    glVertex3f(dx/2, dy/2, dz/2)
    glVertex3f(dx/2, dy/2, -dz/2)
    
    # Front face
    glColor3f(front_color[0], front_color[1], front_color[2])
    glVertex3f(-dx/2, -dy/2, dz/2)
    glVertex3f(dx/2, -dy/2, dz/2)
    glVertex3f(dx/2, dy/2, dz/2)
    glVertex3f(-dx/2, dy/2, dz/2)
    
    # Right face
    glColor3f(side_color[0], side_color[1], side_color[2])
    glVertex3f(dx/2, -dy/2, -dz/2)
    glVertex3f(dx/2, dy/2, -dz/2)
    glVertex3f(dx/2, dy/2, dz/2)
    glVertex3f(dx/2, -dy/2, dz/2)
    
    # Left face
    glColor3f(side_color[0], side_color[1], side_color[2])
    glVertex3f(-dx/2, -dy/2, -dz/2)
    glVertex3f(-dx/2, -dy/2, dz/2)
    glVertex3f(-dx/2, dy/2, dz/2)
    glVertex3f(-dx/2, dy/2, -dz/2)
    
    # Back face
    glColor3f(back_color[0], back_color[1], back_color[2])
    glVertex3f(-dx/2, -dy/2, -dz/2)
    glVertex3f(-dx/2, dy/2, -dz/2)
    glVertex3f(dx/2, dy/2, -dz/2)
    glVertex3f(dx/2, -dy/2, -dz/2)
    
    # Bottom face
    glColor3f(side_color[0], side_color[1], side_color[2])
    glVertex3f(-dx/2, -dy/2, -dz/2)
    glVertex3f(dx/2, -dy/2, -dz/2)
    glVertex3f(dx/2, -dy/2, dz/2)
    glVertex3f(-dx/2, -dy/2, dz/2)
    glEnd()
    
    glPopMatrix()

def draw_human(x, y, z, scale=80):
    """Draw a humanoid figure"""
    global player_angle
    
    quad = gluNewQuadric()
    glPushMatrix()
    
    glTranslatef(x, y, z)
    glRotatef(player_angle, 0, 0, 1)
    glScalef(scale/100, scale/100, scale/100)
    
    # Torso (blue shirt)
    draw_cube_manual_shading(0, 0, 120, 80, 40, 150, [0.2, 0.4, 1.0])
    
    # Head (skin color)
    glPushMatrix()
    glTranslatef(0, 0, 250)
    glColor3f(1.0, 0.8, 0.6)
    gluSphere(quad, 50, 16, 16)
    glPopMatrix()
    
    # Arms (skin color)
    arm_radius = 15
    arm_length = 100
    glColor3f(1.0, 0.8, 0.6)
    
    # Right arm
    glPushMatrix()
    glTranslatef(60, 0, 180)
    glRotatef(-90, 1, 0, 0)
    gluCylinder(quad, arm_radius, arm_radius, arm_length, 8, 8)
    glPopMatrix()
    
    # Left arm
    glPushMatrix()
    glTranslatef(-60, 0, 180)
    glRotatef(-90, 1, 0, 0)
    gluCylinder(quad, arm_radius, arm_radius, arm_length, 8, 8)
    glPopMatrix()
    
    # Legs (skin color)
    leg_radius = 20
    leg_length = 120
    glColor3f(1.0, 0.8, 0.6)
    
    # Right leg
    glPushMatrix()
    glTranslatef(25, 0, 0)
    gluCylinder(quad, leg_radius, leg_radius, leg_length, 8, 8)
    glPopMatrix()
    
    # Left leg
    glPushMatrix()
    glTranslatef(-25, 0, 0)
    gluCylinder(quad, leg_radius, leg_radius, leg_length, 8, 8)
    glPopMatrix()
    
    glPopMatrix()

def draw_perimeter_wall():
    """Draw perimeter wall around buildings"""
    wall_thickness = 200
    wall_height = 400
    wall_color = [0.7, 0.7, 0.6]
    
    buildings_to_encapsulate = [
        castle_configs[0],
        castle_configs[2],
        {'position': central_rock_pos, 'size': 800}
    ]
    
    min_x = min([pos['position'][0] - pos['size']/2 for pos in buildings_to_encapsulate]) - 500
    max_x = max([pos['position'][0] + pos['size']/2 for pos in buildings_to_encapsulate]) + 500
    min_y = min([pos['position'][1] - pos['size']/2 for pos in buildings_to_encapsulate]) - 500
    max_y = max([pos['position'][1] + pos['size']/2 for pos in buildings_to_encapsulate]) + 500
    
    wall_segments = [
        (min_x, max_y, max_x, max_y),
        (max_x, max_y, max_x, min_y),
        (max_x, min_y, min_x, min_y),
        (min_x, min_y, min_x, max_y)
    ]
    
    for x1, y1, x2, y2 in wall_segments:
        draw_wall_segment(x1, y1, x2, y2, 0, wall_thickness, wall_height, wall_color)
        draw_perimeter_stone_blocks(x1, y1, x2, y2, 0, wall_thickness, wall_height)
    
    corners = set()
    for x1, y1, x2, y2 in wall_segments:
        corners.add((x1, y1))
        corners.add((x2, y2))
    
    for corner_x, corner_y in corners:
        draw_guard_tower(corner_x, corner_y, wall_height)

def draw_wall_segment(x1, y1, x2, y2, offset_z, thickness, height, color):
    """Draw a single wall segment"""
    midx = (x1 + x2) / 2
    midy = (y1 + y2) / 2
    length = ((x2 - x1)**2 + (y2 - y1)**2) ** 0.5
    
    glPushMatrix()
    glTranslatef(midx, midy, offset_z + height/2)
    angle = atan2(y2 - y1, x2 - x1) * 180 / 3.14159
    glRotatef(angle, 0, 0, 1)
    draw_cube_manual_shading(0, 0, 0, length, thickness, height, color)
    glPopMatrix()

def draw_perimeter_stone_blocks(x1, y1, x2, y2, offset_z, thickness, height):
    """Draw stone blocks on perimeter walls"""
    length = ((x2 - x1)**2 + (y2 - y1)**2) ** 0.5
    angle = atan2(y2 - y1, x2 - x1) * 180 / 3.14159
    block_width, block_height, gap = 150, 80, 15
    blocks_x = int(length / (block_width + gap))
    blocks_z = int(height / (block_height + gap))
    midx, midy = (x1 + x2) / 2, (y1 + y2) / 2
    
    for row in range(blocks_z):
        for col in range(blocks_x):
            offset = (block_width + gap) / 2 if (row % 2 == 1) else 0
            block_x_local = -length/2 + col * (block_width + gap) + block_width/2 + offset
            block_z_local = row * (block_height + gap) + block_height/2
            
            if abs(block_x_local) > length/2 - block_width/2:
                continue
            
            cos_a, sin_a = cos(radians(angle)), sin(radians(angle))
            world_x = midx + block_x_local * cos_a
            world_y = midy + block_x_local * sin_a
            world_z = offset_z + block_z_local + 15
            
            base_r, base_g, base_b = 0.75, 0.75, 0.65
            variation = 0.1 * ((row + col) % 4 - 2) / 2
            block_color = [
                min(max(base_r + variation, 0.0), 1.0),
                min(max(base_g + variation, 0.0), 1.0),
                min(max(base_b + variation, 0.0), 1.0)
            ]
            
            glPushMatrix()
            glTranslatef(world_x, world_y, world_z)
            glRotatef(angle, 0, 0, 1)
            draw_cube_manual_shading(0, 0, 0, block_width, thickness + 5, block_height, block_color)
            glPopMatrix()

def draw_guard_tower(x, y, wall_height):
    """Draw guard towers at wall corners"""
    tower_radius = 60
    tower_height = wall_height + 200
    tower_color = [0.6, 0.6, 0.55]
    
    quad = gluNewQuadric()
    glPushMatrix()
    glTranslatef(x, y, 0)
    glColor3f(tower_color[0], tower_color[1], tower_color[2])
    gluCylinder(quad, tower_radius, tower_radius, tower_height, 16, 16)
    
    glTranslatef(0, 0, tower_height)
    roof_color = [0.8, 0.3, 0.2]
    glColor3f(roof_color[0], roof_color[1], roof_color[2])
    gluCylinder(quad, tower_radius + 10, 5, tower_radius, 12, 12)
    glPopMatrix()
    
    battlement_color = [0.5, 0.5, 0.45]
    for angle in range(0, 360, 30):
        rad = radians(angle)
        bx = x + (tower_radius + 15) * cos(rad)
        by = y + (tower_radius + 15) * sin(rad)
        draw_cube_manual_shading(bx, by, wall_height + 150, 20, 20, 50, battlement_color)

def draw_rope(start_pos, end_pos, segments=20):
    """Draw a rope between two points with sagging effect"""
    x1, y1, z1 = start_pos
    x2, y2, z2 = end_pos
    glColor3f(0.4, 0.3, 0.2)
    glLineWidth(3.0)
    
    distance = sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)
    sag_factor = min(100, distance * 0.1)
    
    glBegin(GL_LINE_STRIP)
    for i in range(segments + 1):
        t = i / segments
        x = x1 + t * (x2 - x1)
        y = y1 + t * (y2 - y1)
        z = z1 + t * (z2 - z1)
        sag = sag_factor * (4 * t * (1 - t))
        z -= sag
        glVertex3f(x, y, z)
    glEnd()
    glLineWidth(1.0)

def draw_rope_support_bar(x, y, z, height=200):
    """Draw a vertical bar to support ropes"""
    glColor3f(0.3, 0.3, 0.3)
    bar_radius = 8
    
    quad = gluNewQuadric()
    glPushMatrix()
    glTranslatef(x, y, z)
    gluCylinder(quad, bar_radius, bar_radius, height, 16, 16)
    
    glTranslatef(0, 0, height)
    gluDisk(quad, 0, bar_radius, 16, 1)
    
    glTranslatef(0, 0, 5)
    glRotatef(90, 0, 1, 0)
    gluCylinder(quad, 5, 5, 30, 8, 8)
    glPopMatrix()

def draw_platform_with_gap(x, y, z, radius, gap_angle_start=0, gap_angle_end=45, color_scheme='normal'):
    """Draw circular platform with a gap for stairs"""
    platform_thickness = 20
    base_color = [0.7, 0.7, 0.65]
    platform_color = get_color_scheme(color_scheme, base_color)
    
    glPushMatrix()
    glTranslatef(x, y, z + platform_thickness/2)
    glColor3f(platform_color[0], platform_color[1], platform_color[2])
    
    segments = 36
    segment_angle = 360 / segments
    for i in range(segments):
        current_angle = i * segment_angle
        next_angle = (i + 1) * segment_angle
        
        if not (gap_angle_start <= current_angle <= gap_angle_end):
            glBegin(GL_TRIANGLES)
            glVertex3f(0, 0, 0)
            rad1 = radians(current_angle)
            glVertex3f(radius * cos(rad1), radius * sin(rad1), 0)
            rad2 = radians(next_angle)
            glVertex3f(radius * cos(rad2), radius * sin(rad2), 0)
            glEnd()
    
    glPopMatrix()
    
    battlement_base = [0.55, 0.55, 0.55]
    battlement_color = get_color_scheme(color_scheme, battlement_base)
    battlement_z = z + platform_thickness
    
    for angle in range(0, 360, 20):
        if not (gap_angle_start <= angle <= gap_angle_end):
            rad = radians(angle)
            bx = x + (radius + 25) * cos(rad)
            by = y + (radius + 25) * sin(rad)
            draw_cube_manual_shading(bx, by, battlement_z + 30, 35, 35, 80, battlement_color)

def draw_tower_with_platform(offset_x, offset_y, offset_z, radius=160, height=800, floors=3, color_scheme='normal'):
    """Draw tower with platform that has stair entrance gap"""
    quad = gluNewQuadric()
    
    glPushMatrix()
    glTranslatef(offset_x, offset_y, offset_z)
    base_stone_color = [0.82, 0.8, 0.72]
    stone_color = get_color_scheme(color_scheme, base_stone_color)
    glColor3f(stone_color[0], stone_color[1], stone_color[2])
    
    floor_height = height / floors
    for floor in range(floors):
        gluCylinder(quad, radius, radius, floor_height, 32, 32)
        glTranslatef(0, 0, floor_height)
        
        if floor < floors - 1:
            ring_base = [0.6, 0.6, 0.6]
            ring_color = get_color_scheme(color_scheme, ring_base)
            glColor3f(ring_color[0], ring_color[1], ring_color[2])
            gluCylinder(quad, radius + 5, radius + 5, 10, 32, 32)
            glColor3f(stone_color[0], stone_color[1], stone_color[2])
            glTranslatef(0, 0, 10)
    
    glPopMatrix()
    
    platform_z = offset_z + height
    platform_radius = radius + 30
    gap_start = 315
    gap_end = 45
    draw_platform_with_gap(offset_x, offset_y, platform_z, platform_radius, gap_start, gap_end, color_scheme)
    
    central_base = [0.8, 0.8, 0.75]
    central_color = get_color_scheme(color_scheme, central_base)
    draw_cube_manual_shading(offset_x, offset_y, platform_z + 40, 60, 60, 80, central_color)

def draw_rock_tower():
    """Draw central rock tower"""
    x, y, z = central_rock_pos
    rock_color = [0.4, 0.4, 0.35]
    
    draw_cube_manual_shading(x, y, z + 256, 352, 330, 413, rock_color)
    draw_cube_manual_shading(x - 15, y + 8, z + 650, 308, 286, 375, rock_color)
    draw_cube_manual_shading(x + 12, y - 10, z + 1006, 264, 242, 338, rock_color)
    draw_cube_manual_shading(x - 5, y + 5, z + 1300, 220, 198, 250, rock_color)
    draw_cube_manual_shading(x, y, z + 1488, 165, 154, 125, rock_color)

def draw_rock_tower_platform():
    """Draw simple platform on top of rock tower"""
    x, y, z = central_rock_pos
    platform_height = z + 1600
    platform_radius = 120
    platform_thickness = 30
    platform_color = [0.6, 0.6, 0.55]
    
    glColor3f(platform_color[0], platform_color[1], platform_color[2])
    draw_filled_circle(x, y, platform_height + platform_thickness/2, platform_radius)
    
    railing_color = [0.5, 0.5, 0.45]
    railing_height = platform_height + platform_thickness + 10
    for angle in range(0, 360, 30):
        rad = radians(angle)
        rail_x = x + (platform_radius - 10) * cos(rad)
        rail_y = y + (platform_radius - 10) * sin(rad)
        draw_cube_manual_shading(rail_x, rail_y, railing_height + 15, 8, 8, 30, railing_color)

def draw_filled_circle(x, y, z, radius, segments=32):
    """Draw a filled circular plate using triangle fan"""
    glPushMatrix()
    glTranslatef(x, y, z)
    glBegin(GL_TRIANGLE_FAN)
    glVertex3f(0.0, 0.0, 0.0)
    for i in range(segments + 1):
        angle = 2 * 3.14159 * i / segments
        px = radius * cos(angle)
        py = radius * sin(angle)
        glVertex3f(px, py, 0.0)
    glEnd()
    glPopMatrix()

def draw_spiral_stairs_around_rock():
    """Draw spiral stairs around rock tower"""
    x, y, z = central_rock_pos
    radius = 220
    steps = 80
    total_height = 1600
    height_per_step = total_height / steps
    angle_per_step = 1800 / steps
    stair_color = [0.6, 0.5, 0.4]
    
    for i in range(steps):
        angle = radians(angle_per_step * i)
        step_x = x + radius * cos(angle)
        step_y = y + radius * sin(angle)
        step_z = z + height_per_step * i
        
        glPushMatrix()
        glTranslatef(step_x, step_y, step_z)
        glRotatef(angle_per_step * i, 0, 0, 1)
        draw_cube_manual_shading(0, 0, 0, 100, 50, 15, stair_color)
        
        if i % 10 == 0:
            draw_cube_manual_shading(0, 0, -50, 25, 25, 100, stair_color)
        glPopMatrix()

def draw_rope_connections():
    """Draw ropes connecting towers to castle centers and rock tower"""
    for config in castle_configs:
        pos = config['position']
        wall_height = config['wall_height']
        
        castle_center_height = pos[2] + wall_height
        castle_center = [pos[0], pos[1], castle_center_height]
        
        bar_height = 350
        draw_rope_support_bar(castle_center[0], castle_center[1], castle_center[2], bar_height)
        
        center_bar_top = [castle_center[0], castle_center[1], castle_center[2] + bar_height - 50]
        rock_platform = [central_rock_pos[0], central_rock_pos[1], central_rock_pos[2] + 1600 + 150]
        draw_rope(center_bar_top, rock_platform)
    
    draw_rope_support_bar(central_rock_pos[0], central_rock_pos[1], central_rock_pos[2] + 1600 + 30, 100)

def draw_wall(x1, y1, x2, y2, offset_z, thickness=400, height=600, color_scheme='normal'):
    """Draw wall segment"""
    midx = (x1 + x2) / 2
    midy = (y1 + y2) / 2
    length = ((x2 - x1)**2 + (y2 - y1)**2) ** 0.5
    
    glPushMatrix()
    glTranslatef(midx, midy, offset_z + height/2)
    angle = atan2(y2 - y1, x2 - x1) * 180 / 3.14159
    glRotatef(angle, 0, 0, 1)
    wall_base = [0.85, 0.82, 0.75]
    wall_color = get_color_scheme(color_scheme, wall_base)
    draw_cube_manual_shading(0, 0, 0, length, thickness, height, wall_color)
    glPopMatrix()

def draw_stone_block(x, y, z, width, depth, height, angle, row, col, color_scheme='normal'):
    """Draw individual stone block"""
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(angle, 0, 0, 1)
    
    base_r, base_g, base_b = 0.85, 0.40, 0.35
    variation = 0.12 * ((row + col) % 5 - 2) / 2
    stone_color = [
        min(max(base_r + variation, 0.0), 1.0),
        min(max(base_g + variation, 0.0), 1.0),
        min(max(base_b + variation, 0.0), 1.0)
    ]
    
    final_color = get_color_scheme(color_scheme, stone_color)
    draw_cube_manual_shading(0, 0, 0, width, depth, height, final_color)
    glPopMatrix()

def draw_stone_blocks(x1, y1, x2, y2, offset_z, thickness, height, color_scheme='normal'):
    """Draw stone blocks on walls"""
    length = ((x2 - x1)**2 + (y2 - y1)**2) ** 0.5
    angle = atan2(y2 - y1, x2 - x1) * 180 / 3.14159
    block_width, block_height, gap = 200, 100, 20
    blocks_x = int(length / (block_width + gap))
    blocks_z = int(height / (block_height + gap))
    midx, midy = (x1 + x2) / 2, (y1 + y2) / 2
    
    for row in range(blocks_z):
        for col in range(blocks_x):
            offset = (block_width + gap) / 2 if (row % 2 == 1) else 0
            block_x_local = -length/2 + col * (block_width + gap) + block_width/2 + offset
            block_z_local = row * (block_height + gap) + block_height/2
            
            if abs(block_x_local) > length/2 - block_width/2:
                continue
            
            cos_a, sin_a = cos(radians(angle)), sin(radians(angle))
            world_x = midx + block_x_local * cos_a
            world_y = midy + block_x_local * sin_a
            world_z = offset_z + block_z_local + 15
            
            draw_stone_block(world_x, world_y, world_z, block_width, thickness + 5, block_height, angle, row, col, color_scheme)

def draw_single_castle(config):
    """Draw individual castle"""
    pos = config['position']
    size = config['size']
    height = config['height']
    tower_radius = config['tower_radius']
    floors = config['floors']
    wall_thickness = config['wall_thickness']
    wall_height = config['wall_height']
    color_scheme = config['color_scheme']
    
    half_size = size / 2
    corners = [
        (pos[0] + half_size, pos[1] + half_size),
        (pos[0] - half_size, pos[1] + half_size),
        (pos[0] - half_size, pos[1] - half_size),
        (pos[0] + half_size, pos[1] - half_size)
    ]
    
    for (x, y) in corners:
        draw_tower_with_platform(x, y, pos[2], tower_radius, height, floors, color_scheme)
    
    wall_inset = 50
    for i in range(len(corners)):
        x1, y1 = corners[i]
        x2, y2 = corners[(i + 1) % len(corners)]
        
        dx, dy = x2 - x1, y2 - y1
        length = (dx**2 + dy**2)**0.5
        
        dx_norm, dy_norm = dx / length * wall_inset, dy / length * wall_inset
        wall_x1, wall_y1 = x1 + dx_norm, y1 + dy_norm
        wall_x2, wall_y2 = x2 - dx_norm, y2 - dy_norm
        
        draw_wall(wall_x1, wall_y1, wall_x2, wall_y2, pos[2], wall_thickness, wall_height, color_scheme)
        draw_stone_blocks(wall_x1, wall_y1, wall_x2, wall_y2, pos[2], wall_thickness, wall_height, color_scheme)
    
    railing_height = 80
    railing_color = get_color_scheme(color_scheme, [0.6, 0.6, 0.55])
    railing_top_z = pos[2] + wall_height + railing_height/2
    
    for i in range(len(corners)):
        x1, y1 = corners[i]
        x2, y2 = corners[(i + 1) % len(corners)]
        
        dx, dy = x2 - x1, y2 - y1
        length = (dx**2 + dy**2)**0.5
        
        dx_norm, dy_norm = dx / length * wall_inset, dy / length * wall_inset
        wall_x1, wall_y1 = x1 + dx_norm, y1 + dy_norm
        wall_x2, wall_y2 = x2 - dx_norm, y2 - dy_norm
        
        num_railings = int(length / 100)
        for j in range(num_railings + 1):
            t = j / max(num_railings, 1)
            rail_x = wall_x1 + t * (wall_x2 - wall_x1)
            rail_y = wall_y1 + t * (wall_y2 - wall_y1)
            draw_cube_manual_shading(rail_x, rail_y, railing_top_z, 15, 15, railing_height, railing_color)
    
    railing_bar_color = get_color_scheme(color_scheme, [0.65, 0.65, 0.6])
    for i in range(len(corners)):
        x1, y1 = corners[i]
        x2, y2 = corners[(i + 1) % len(corners)]
        
        dx, dy = x2 - x1, y2 - y1
        length = (dx**2 + dy**2)**0.5
        
        dx_norm, dy_norm = dx / length * wall_inset, dy / length * wall_inset
        wall_x1, wall_y1 = x1 + dx_norm, y1 + dy_norm
        wall_x2, wall_y2 = x2 - dx_norm, y2 - dy_norm
        
        midx = (wall_x1 + wall_x2) / 2
        midy = (wall_y1 + wall_y2) / 2
        
        glPushMatrix()
        glTranslatef(midx, midy, pos[2] + wall_height + railing_height - 20)
        angle = atan2(wall_y2 - wall_y1, wall_x2 - wall_x1) * 180 / 3.14159
        glRotatef(angle, 0, 0, 1)
        draw_cube_manual_shading(0, 0, 0, length - 2*wall_inset, 10, 8, railing_bar_color)
        glPopMatrix()
    
    interior_base = [0.82, 0.8, 0.72]
    gate_base = [0.3, 0.3, 0.3]
    interior_color = get_color_scheme(color_scheme, interior_base)
    gate_color = get_color_scheme(color_scheme, gate_base)
    
    draw_cube_manual_shading(pos[0], pos[1], pos[2] + wall_height/2, size * 0.8, size * 0.8, wall_height, interior_color)
    draw_cube_manual_shading(pos[0], pos[1] - half_size + wall_inset, pos[2] + wall_height/2, 300, 80, wall_height, gate_color)

def draw_simple_tree(x, y, z, size=100):
    """Draw a simple tree"""
    quad = gluNewQuadric()
    
    glPushMatrix()
    glTranslatef(x, y, z)
    glColor3f(0.4, 0.2, 0.1)
    gluCylinder(quad, size*0.15, size*0.1, size*0.8, 6, 10)
    
    glTranslatef(0, 0, size*0.6)
    glColor3f(0.1, 0.5, 0.1)
    gluSphere(quad, size*0.6, 8, 8)
    glPopMatrix()

def draw_simple_bush(x, y, z, size=60):
    """Draw a simple bush"""
    quad = gluNewQuadric()
    
    glPushMatrix()
    glTranslatef(x, y, z + size*0.4)
    glColor3f(0.2, 0.4, 0.2)
    gluSphere(quad, size*0.5, 6, 6)
    glPopMatrix()

def draw_multi_colored_grid():
    """Draw a grid with multiple shades of green"""
    grid_size = GRID_LENGTH * 20
    quad_size = 800
    num_quads = (grid_size * 2) // quad_size
    
    green_colors = [
        [0.15, 0.4, 0.15], [0.2, 0.5, 0.2], [0.25, 0.6, 0.25], [0.3, 0.7, 0.3],
        [0.35, 0.75, 0.35], [0.4, 0.8, 0.4], [0.2, 0.45, 0.2], [0.18, 0.55, 0.18]
    ]
    
    for i in range(num_quads):
        for j in range(num_quads):
            x1 = -grid_size + i * quad_size
            y1 = -grid_size + j * quad_size
            x2 = x1 + quad_size
            y2 = y1 + quad_size
            
            color_index = (i + j) % len(green_colors)
            color = green_colors[color_index]
            
            glColor3f(color[0], color[1], color[2])
            glBegin(GL_QUADS)
            glVertex3f(x1, y1, 0)
            glVertex3f(x2, y1, 0)
            glVertex3f(x2, y2, 0)
            glVertex3f(x1, y2, 0)
            glEnd()
    
    glColor3f(0.1, 0.3, 0.1)
    glLineWidth(1.0)
    glBegin(GL_LINES)
    for i in range(num_quads + 1):
        line_x = -grid_size + i * quad_size
        glVertex3f(line_x, -grid_size, 1)
        glVertex3f(line_x, grid_size, 1)
    
    for j in range(num_quads + 1):
        line_y = -grid_size + j * quad_size
        glVertex3f(-grid_size, line_y, 1)
        glVertex3f(grid_size, line_y, 1)
    glEnd()

def draw_minimal_vegetation():
    """Add minimal vegetation"""
    tree_positions = [
        (-5000, -3000), (-4000, 2000), (-2000, -4000), (3000, -2000), (4000, 3000),
        (-6000, 1000), (2000, -5000), (5000, -1000), (-1000, -6000), (6000, 2000),
        (-3000, 4000), (1000, 5000), (-5000, 0), (0, -3000), (4000, 0)
    ]
    
    bush_positions = [
        (-4500, -2500), (-3500, 1500), (-1500, -3500), (2500, -1500), (3500, 2500),
        (-5500, 500), (1500, -4500), (4500, -500), (-500, -5500), (5500, 1500),
        (-2500, 3500), (500, 4500), (-4500, -500), (-500, -2500), (3500, -500),
        (-1500, 4500), (4500, 500), (-3500, -1500), (2500, 3500), (-500, 5500),
        (-6000, -1000), (1000, -6000), (6000, 1000), (-1000, 6000), (0, -4000)
    ]
    
    def is_safe_position(x, y):
        castle_centers = [[-800, -1600], [900, 1000], [-3300, 400], [-1000, 1500]]
        for cx, cy in castle_centers:
            if sqrt((x - cx)**2 + (y - cy)**2) < 900:
                return False
        return True
    
    for x, y in tree_positions:
        if is_safe_position(x, y):
            draw_simple_tree(x, y, 30, 240)
    
    for x, y in bush_positions:
        if is_safe_position(x, y):
            draw_simple_bush(x, y, 0, 190)

def draw_mountain_range():
    """Draw dense clusters of rocky mountains around the scene"""
    mountain_positions = [
        (-2746, 6714, 0, 825, 1079, 740), (-1150, 8828, 0, 942, 1077, 652),
        (-2708, 7358, 0, 1358, 744, 816), (-1368, 8630, 0, 895, 811, 719),
        (-2883, 7216, 0, 827, 987, 701), (-1100, 9100, 0, 1200, 900, 800),
        (-2600, 6900, 0, 1000, 850, 750),
        (-167, -6735, 0, 1358, 914, 712), (-2441, -8797, 0, 1084, 703, 681),
        (-186, -6968, 0, 1148, 842, 679), (-2680, -8619, 0, 1144, 752, 647),
        (-511, -7301, 0, 1167, 876, 735), (-2300, -8800, 0, 1100, 800, 700),
        (-800, -7000, 0, 900, 750, 650),
        (6644, -1653, 0, 1270, 974, 663), (8987, -320, 0, 1365, 850, 785),
        (7191, -2204, 0, 871, 723, 716), (9391, -104, 0, 881, 819, 651),
        (6989, -2116, 0, 1264, 1025, 786), (9100, 200, 0, 1000, 900, 750),
        (6800, -2000, 0, 1200, 850, 700),
        (-7234, 479, 0, 1163, 807, 736), (-8682, -1201, 0, 873, 1011, 687),
        (-6854, 846, 0, 1050, 783, 836), (-9012, -1624, 0, 1370, 812, 766),
        (-6614, 894, 0, 857, 817, 616), (-8900, -1400, 0, 1100, 950, 800),
        (-7200, 700, 0, 950, 800, 650)
    ]
    
    for x, y, z, width, height, depth in mountain_positions:
        draw_rocky_mountain(x, y, z, width, height, depth)

def draw_rocky_mountain(x, y, z, width=800, height=600, depth=600):
    """Draw a rocky mountain using quadric objects"""
    quad = gluNewQuadric()
    base_color = [0.5, 0.4, 0.35]
    
    glPushMatrix()
    glTranslatef(x, y, z)
    glColor3f(base_color[0], base_color[1], base_color[2])
    
    glPushMatrix()
    glScalef(width/200, depth/200, height/200)
    gluSphere(quad, 100, 12, 8)
    glPopMatrix()
    
    glPopMatrix()

def draw_all_structures():
    """Draw complete castle complex"""
    for config in castle_configs:
        draw_single_castle(config)
    
    draw_rock_tower()
    draw_rock_tower_platform()
    draw_spiral_stairs_around_rock()
    draw_rope_connections()
    draw_perimeter_wall()
    draw_human(player_pos[0], player_pos[1], player_pos[2], scale=60)
    
    draw_enemies()
    draw_castle_hp_bars()

def draw_text(x, y, text, font=None):
    """Draw text on screen"""
    if font is None:
        font = GLUT_BITMAP_HELVETICA_18
    
    glPushAttrib(GL_ENABLE_BIT | GL_CURRENT_BIT)
    glDisable(GL_LIGHTING)
    glDisable(GL_DEPTH_TEST)
    glColor3f(1, 1, 1)
    
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    
    glPopAttrib()

def clamp_player_position():
    """Player position clamping"""
    global player_pos, teleport_skip_clamp
    
    if teleport_skip_clamp:
        teleport_skip_clamp = False
        return
    
    x, y, z = player_pos
    
    def get_castle_boundaries(castle_config):
        """Get exact castle boundaries"""
        pos = castle_config['position']
        size = castle_config['size']
        wall_height = castle_config['wall_height']
        wall_inset = 50
        
        half_size = size / 2
        min_x = pos[0] - half_size + wall_inset
        max_x = pos[0] + half_size - wall_inset
        min_y = pos[1] - half_size + wall_inset
        max_y = pos[1] + half_size - wall_inset
        z_min = 0
        z_max = pos[2] + wall_height + 200
        
        return min_x, max_x, min_y, max_y, z_min, z_max
    
    for i, castle in enumerate(castle_configs):
        min_x, max_x, min_y, max_y, z_min, z_max = get_castle_boundaries(castle)
        
        BUFFER_ZONE = 100

        if (min_x - BUFFER_ZONE <= x <= max_x + BUFFER_ZONE and 
            min_y - BUFFER_ZONE <= y <= max_y + BUFFER_ZONE and 
            z_min <= z <= z_max):
            
            player_pos[0] = max(min_x, min(x, max_x))
            player_pos[1] = max(min_y, min(y, max_y))
            player_pos[2] = max(z_min, min(z, z_max))
            return
    
    rock_x, rock_y, rock_z = central_rock_pos
    rock_radius = 120
    rock_height_min = rock_z + 1600
    rock_height_max = rock_z + 1800
    
    if rock_height_min <= z <= rock_height_max:
        dist_from_center = sqrt((x - rock_x)**2 + (y - rock_y)**2)
        if dist_from_center <= rock_radius:
            if dist_from_center > rock_radius - 10:
                direction_x = (x - rock_x) / max(dist_from_center, 0.1)
                direction_y = (y - rock_y) / max(dist_from_center, 0.1)
                player_pos[0] = rock_x + direction_x * (rock_radius - 10)
                player_pos[1] = rock_y + direction_y * (rock_radius - 10)
            return
    
    if rock_z <= z <= rock_z + 1600:
        stair_radius = 220
        dist_from_rock = sqrt((x - rock_x)**2 + (y - rock_y)**2)
        if 180 <= dist_from_rock <= 260:
            return
    
    buildings = [castle_configs[0], castle_configs[2], {'position': central_rock_pos, 'size': 800}]
    min_x = min([pos['position'][0] - pos['size']/2 for pos in buildings]) - 500
    max_x = max([pos['position'][0] + pos['size']/2 for pos in buildings]) + 500
    min_y = min([pos['position'][1] - pos['size']/2 for pos in buildings]) - 500
    max_y = max([pos['position'][1] + pos['size']/2 for pos in buildings]) + 500
    
    if 0 <= z <= 450:
        if min_x <= x <= max_x and min_y <= y <= max_y:
            if x < min_x: player_pos[0] = min_x
            elif x > max_x: player_pos[0] = max_x
            
            if y < min_y: player_pos[1] = min_y
            elif y > max_y: player_pos[1] = max_y
            return
    
    min_dist = float('inf')
    nearest_castle = None
    
    for castle in castle_configs:
        cx, cy = castle['position'][0], castle['position'][1]
        dist = sqrt((x - cx)**2 + (y - cy)**2)
        if dist < min_dist:
            min_dist = dist
            nearest_castle = castle
    
    if nearest_castle:
        min_x, max_x, min_y, max_y, z_min, z_max = get_castle_boundaries(nearest_castle)
        
        clamp_x = max(min_x, min(x, max_x))
        clamp_y = max(min_y, min(y, max_y))
        
        player_pos[0] = clamp_x
        player_pos[1] = clamp_y
        player_pos[2] = nearest_castle['position'][2] + nearest_castle['wall_height']

def setup_camera():
    """Setup camera perspective"""
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, 1.25, 0.1, 30000)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    
    eye_x = cam_dist * cos(radians(cam_angle_v)) * cos(radians(cam_angle_h))
    eye_y = cam_dist * cos(radians(cam_angle_v)) * sin(radians(cam_angle_h))
    eye_z = cam_dist * sin(radians(cam_angle_v))
    
    gluLookAt(eye_x + player_pos[0], eye_y + player_pos[1], eye_z + player_pos[2],
              player_pos[0], player_pos[1], player_pos[2], 0, 0, 1)

def show_screen():
    """Main display function"""
    global game_time, last_spawn_time
    
    current_time = time.time()
    if game_time == 0:
        game_time = current_time
        last_spawn_time = current_time
    
    dt = min(0.1, current_time - game_time)
    game_time = current_time
    
    if current_time - last_spawn_time > spawn_interval:
        spawn_enemy()
        last_spawn_time = current_time
        print(f"Spawned enemy! Total enemies: {len(enemies)}")
    
    if dt > 0:
        update_enemies(dt)
    
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, 1000, 800)
    setup_camera()
    
    draw_multi_colored_grid()
    draw_all_structures()
    draw_mountain_range()
    draw_minimal_vegetation()
    
    draw_text(10, 770, f"Castle Defense - Under Attack!")
    draw_text(10, 740, "Controls: Arrows=Rotate, Z/X=Zoom, WASD=Move, SPACE=Shoot")
    draw_text(10, 710, "Teleport: 1/2/3=Castles, T=Tower Top, G=Ground")
    draw_text(10, 680, f"Position: ({int(player_pos[0])}, {int(player_pos[1])}, {int(player_pos[2])})")
    draw_text(10, 650, f"Enemies: {len(enemies)}")
    
    draw_text(10, 620, f"Castle 1 HP: {castle_hp[0]}/{castle_max_hp[0]}")
    draw_text(10, 590, f"Castle 3 HP: {castle_hp[2]}/{castle_max_hp[2]}")
    
    glutSwapBuffers()

def handle_special_keys(key, x, y):
    """Handle arrow keys"""
    global cam_angle_h, cam_angle_v
    
    if key == GLUT_KEY_LEFT:
        cam_angle_h -= 5
    elif key == GLUT_KEY_RIGHT:
        cam_angle_h += 5
    elif key == GLUT_KEY_UP:
        cam_angle_v = min(89, cam_angle_v + 5)
    elif key == GLUT_KEY_DOWN:
        cam_angle_v = max(-10, cam_angle_v - 5)
    
    glutPostRedisplay()

def player_shoot():
    """Player shoots at nearest enemy"""
    if not enemies:
        return
    
    nearest_enemy = None
    min_distance = float('inf')
    
    for enemy in enemies:
        dx = enemy.pos[0] - player_pos[0]
        dy = enemy.pos[1] - player_pos[1]
        dz = enemy.pos[2] - player_pos[2]
        distance = sqrt(dx*dx + dy*dy + dz*dz)
        
        if distance < min_distance:
            min_distance = distance
            nearest_enemy = enemy
    
    if nearest_enemy and min_distance < 2000:
        if nearest_enemy.take_damage(50):
            effects.append(ExplosionEffect(nearest_enemy.pos))

def handle_keyboard(key, x, y):
    """Keyboard input"""
    global cam_dist, player_pos, player_angle, player_speed, player_turn_speed, teleport_skip_clamp
    
    k = key.decode("utf-8").lower()
    
    if k == 'z':
        cam_dist = max(1000, cam_dist - 150)
    elif k == 'x':
        cam_dist = min(25000, cam_dist + 150)
    elif k == 'a':
        player_angle += player_turn_speed
    elif k == 'd':
        player_angle -= player_turn_speed
    elif k == 'w':
        rad = radians(player_angle + 90)
        player_pos[0] += player_speed * cos(rad)
        player_pos[1] += player_speed * sin(rad)
        clamp_player_position()
    elif k == 's':
        rad = radians(player_angle + 90)
        player_pos[0] -= player_speed * cos(rad)
        player_pos[1] -= player_speed * sin(rad)
        clamp_player_position()
    elif k in ['1', '2', '3']:
        teleport_skip_clamp = True
        index = int(k) - 1
        castle = castle_configs[index]
        tx, ty, base_z = castle['position']
        tz = base_z + castle['wall_height']
        
        player_pos[0] = float(tx)
        player_pos[1] = float(ty)
        player_pos[2] = float(tz)
        print(f"Teleported to Castle {k}")
    elif k == 't':
        teleport_skip_clamp = True
        player_pos[0] = central_rock_pos[0]
        player_pos[1] = central_rock_pos[1] 
        player_pos[2] = central_rock_pos[2] + 1630
        print(f"Teleported to Tower Top")
    elif k == 'g':
        teleport_skip_clamp = True
        ground_level = 50
        player_pos[2] = ground_level
        print(f"Dropped to ground")
        clamp_player_position()
    elif key == b' ':
        player_shoot()
    
    glutPostRedisplay()

def main():
    """Main function"""
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"Castle Defense - Wall Attack Fixed!")
    
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LESS)
    glClearColor(0.0, 0.0, 0.2, 1.0)
    
    glutIdleFunc(lambda: glutPostRedisplay())
    glutDisplayFunc(show_screen)
    glutKeyboardFunc(handle_keyboard)
    glutSpecialFunc(handle_special_keys)
    glutMainLoop()

if __name__ == "__main__":
    main()

