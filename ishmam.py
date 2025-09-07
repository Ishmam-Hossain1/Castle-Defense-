from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from math import sin, cos, atan2, radians, sqrt
import time

GRID_LENGTH = 500
# cam_angle_h = 45
# cam_angle_v = 30
# cam_dist = 8000  # Increased for better view of perimeter wall
fovY = 60

# Initial camera settings
camera_radius = 8000
camera_height = 2500
cam_angle_h = radians(45)  # horizontal angle
min_radius = 500
max_radius = 20000

# Compute initial camera_pos based on angle and radius
camera_pos = [
    camera_radius * cos(cam_angle_h),  # X
    camera_radius * sin(cam_angle_h),  # Y
    camera_height                     # Z
]


fpp_mode = False  # False = default view, True = FPP

import time

player_coins = 0
castle_health = 100   # initial health
max_castle_health = 200

last_chest_time = 0  # timestamp of last chest collection
CHEST_COOLDOWN = 5   # seconds


player_arrows = 0  # initial arrow count


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
        'color_scheme': 'reddish',
        'chest': None
    },
    {
        'position': [900, 1000, 0],    # Biggest castle - EXCLUDED from wall
        'size': 1600,
        'height': 1200,
        'roof_z': 800,
        'tower_radius': 180,
        'floors': 12,
        'wall_thickness': 400,
        'wall_height': 800,
        'color_scheme': 'reddish',
        'chest': {
            'position': [1200, 500, 0],   # near the east inner wall
            'size': 100
        }
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
        'color_scheme': 'reddish',
        'chest': None
    }
]

# Central rock tower position
central_rock_pos = [-1000, 1500, 0]

player_pos = [central_rock_pos[0], central_rock_pos[1], central_rock_pos[2] + 1630]
player_speed = 50          # movement step size
player_angle = 0           # in degrees, 0 = facing along +Y
player_turn_speed = 5      # degrees per key press



def get_color_scheme(scheme_name, base_color):
    """Get color based on scheme"""
    if scheme_name == 'reddish':
        return [min(1.0, base_color[0] * 1.2), base_color[1] * 0.8, base_color[2] * 0.8]
    else:
        return base_color

def draw_cube_manual_shading(x, y, z, dx, dy, dz, color):
    """Draw a simple cube at (x, y, z) with size (dx, dy, dz) and flat color."""
    glPushMatrix()
    glTranslatef(x, y, z)
    glColor3f(*color)
    
    glBegin(GL_QUADS)
    
    # Top face
    glVertex3f(-dx/2, dy/2, -dz/2)
    glVertex3f(-dx/2, dy/2, dz/2)
    glVertex3f(dx/2, dy/2, dz/2)
    glVertex3f(dx/2, dy/2, -dz/2)
    
    # Bottom face
    glVertex3f(-dx/2, -dy/2, -dz/2)
    glVertex3f(dx/2, -dy/2, -dz/2)
    glVertex3f(dx/2, -dy/2, dz/2)
    glVertex3f(-dx/2, -dy/2, dz/2)
    
    # Front face
    glVertex3f(-dx/2, -dy/2, dz/2)
    glVertex3f(dx/2, -dy/2, dz/2)
    glVertex3f(dx/2, dy/2, dz/2)
    glVertex3f(-dx/2, dy/2, dz/2)
    
    # Back face
    glVertex3f(-dx/2, -dy/2, -dz/2)
    glVertex3f(-dx/2, dy/2, -dz/2)
    glVertex3f(dx/2, dy/2, -dz/2)
    glVertex3f(dx/2, -dy/2, -dz/2)
    
    # Left face
    glVertex3f(-dx/2, -dy/2, -dz/2)
    glVertex3f(-dx/2, -dy/2, dz/2)
    glVertex3f(-dx/2, dy/2, dz/2)
    glVertex3f(-dx/2, dy/2, -dz/2)
    
    # Right face
    glVertex3f(dx/2, -dy/2, -dz/2)
    glVertex3f(dx/2, dy/2, -dz/2)
    glVertex3f(dx/2, dy/2, dz/2)
    glVertex3f(dx/2, -dy/2, dz/2)
    
    glEnd()
    glPopMatrix()


from math import radians
from OpenGL.GL import *
from OpenGL.GLU import *

def draw_human(x, y, z, scale=80):
    """Draw a humanoid figure with blue torso, skin-colored limbs, and arms pointing forward."""
    global player_angle
    quad = gluNewQuadric()
    glPushMatrix()
    
    # Move to human position
    glTranslatef(x, y, z)
    
    # Rotate human to face player_angle
    glRotatef(player_angle, 0, 0, 1)  # rotate around Z-axis
    
    # Scale human
    glScalef(scale/100, scale/100, scale/100)
    
    # Torso (blue shirt)
    draw_cube_manual_shading(0, 0, 120, 80, 40, 150, [0.2, 0.4, 1.0])
    
    # Head (skin color)
    glPushMatrix()
    glTranslatef(0, 0, 250)
    glColor3f(1.0, 0.8, 0.6)
    gluSphere(quad, 50, 16, 16)
    glPopMatrix()
    
    # Arms (skin color) - pointing forward
    arm_radius = 15
    arm_length = 100
    glColor3f(1.0, 0.8, 0.6)

    # Right arm
    glPushMatrix()
    glTranslatef(60, 0, 180)  # shoulder position
    glRotatef(-90, 1, 0, 0)   # point forward
    gluCylinder(quad, arm_radius, arm_radius, arm_length, 8, 8)
    glPopMatrix()

    # Left arm
    glPushMatrix()
    glTranslatef(-60, 0, 180)  # shoulder position
    glRotatef(-90, 1, 0, 0)    # point forward
    gluCylinder(quad, arm_radius, arm_radius, arm_length, 8, 8)
    glPopMatrix()
    
    # Legs (skin color)
    leg_radius = 20
    leg_length = 120
    glColor3f(1.0, 0.8, 0.6)

    # Right leg
    glPushMatrix()
    glTranslatef(25, 0, 0)
    glRotatef(0, 1, 0, 0)
    gluCylinder(quad, leg_radius, leg_radius, leg_length, 8, 8)
    glPopMatrix()

    # Left leg
    glPushMatrix()
    glTranslatef(-25, 0, 0)
    glRotatef(0, 1, 0, 0)
    gluCylinder(quad, leg_radius, leg_radius, leg_length, 8, 8)
    glPopMatrix()

    glPopMatrix()





def draw_perimeter_wall():
    """Draw perimeter wall around all buildings except the biggest castle"""
    # Define perimeter wall boundaries
    # Include: castle[0], castle[2], and central rock tower
    # Exclude: castle[1] (biggest castle)
    
    wall_thickness = 200
    wall_height = 400
    wall_color = [0.7, 0.7, 0.6]  # Light gray wall
    
    # Calculate bounding box for buildings to encapsulate (excluding biggest castle)
    buildings_to_encapsulate = [
        castle_configs[0],  # First castle
        castle_configs[2],  # Third castle
        {'position': central_rock_pos, 'size': 800}  # Rock tower area
    ]
    
    # Find min/max coordinates with padding
    min_x = min([pos['position'][0] - pos['size']/2 for pos in buildings_to_encapsulate]) - 500
    max_x = max([pos['position'][0] + pos['size']/2 for pos in buildings_to_encapsulate]) + 500
    min_y = min([pos['position'][1] - pos['size']/2 for pos in buildings_to_encapsulate]) - 500
    max_y = max([pos['position'][1] + pos['size']/2 for pos in buildings_to_encapsulate]) + 500
    
    # Define wall segments (rectangular perimeter)
    wall_segments = [
        # North wall
        (min_x, max_y, max_x, max_y),
        # East wall  
        (max_x, max_y, max_x, min_y),
        # South wall
        (max_x, min_y, min_x, min_y),
        # West wall
        (min_x, min_y, min_x, max_y)
    ]
    
    for x1, y1, x2, y2 in wall_segments:
        draw_wall_segment(x1, y1, x2, y2, 0, wall_thickness, wall_height, wall_color)
        
        # Add stone block texture to perimeter walls
        draw_perimeter_stone_blocks(x1, y1, x2, y2, 0, wall_thickness, wall_height)

    # Collect all unique corner positions from wall segments
    corners = set()
    for x1, y1, x2, y2 in wall_segments:
        corners.add((x1, y1))  # Start point
        corners.add((x2, y2))  # End point

    # Draw guard towers at all unique corners (guaranteed 4 corners)
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
            
            # Color variation for perimeter wall blocks
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
    
    # Tower roof
    glTranslatef(0, 0, tower_height)
    roof_color = [0.8, 0.3, 0.2]  # Red roof
    glColor3f(roof_color[0], roof_color[1], roof_color[2])
    gluCylinder(quad, tower_radius + 10, 5, tower_radius, 12, 12)
    
    glPopMatrix()
    
    # Battlements around tower top
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
    
    glColor3f(0.4, 0.3, 0.2)  # Brown rope color
    glLineWidth(3.0)
    
    # Calculate rope sag
    distance = sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)
    sag_factor = min(100, distance * 0.1)
    
    glBegin(GL_LINE_STRIP)
    for i in range(segments + 1):
        t = i / segments
        
        # Linear interpolation
        x = x1 + t * (x2 - x1)
        y = y1 + t * (y2 - y1)
        z = z1 + t * (z2 - z1)
        
        # Add sag (parabolic curve)
        sag = sag_factor * (4 * t * (1 - t))
        z -= sag
        
        glVertex3f(x, y, z)
    glEnd()
    
    glLineWidth(1.0)

def draw_rope_support_bar(x, y, z, height=200):
    """Draw a vertical bar to support ropes"""
    glColor3f(0.3, 0.3, 0.3)  # Dark gray
    bar_radius = 8
    
    # Main pole
    quad = gluNewQuadric()
    glPushMatrix()
    glTranslatef(x, y, z)
    gluCylinder(quad, bar_radius, bar_radius, height, 16, 16)
    
    # Top cap
    glTranslatef(0, 0, height)
    gluDisk(quad, 0, bar_radius, 16, 1)
    
    # Cross beam on top for rope attachment
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
    
    # Draw platform in segments to create gap
    segments = 36
    segment_angle = 360 / segments
    
    for i in range(segments):
        current_angle = i * segment_angle
        next_angle = (i + 1) * segment_angle
        
        # Skip segments that fall within the gap
        if not (gap_angle_start <= current_angle <= gap_angle_end):
            glBegin(GL_TRIANGLES)
            glVertex3f(0, 0, 0)
            rad1 = radians(current_angle)
            glVertex3f(radius * cos(rad1), radius * sin(rad1), 0)
            rad2 = radians(next_angle)
            glVertex3f(radius * cos(rad2), radius * sin(rad2), 0)
            glEnd()
    
    glPopMatrix()
    
    # Add battlements around platform (excluding gap area)
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
    
    # Draw main tower
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
    
    # Add platform with gap for stairs
    platform_z = offset_z + height
    platform_radius = radius + 30
    
    # Create gap facing outward from castle center
    gap_start = 315
    gap_end = 45
    
    draw_platform_with_gap(offset_x, offset_y, platform_z, platform_radius,
                          gap_start, gap_end, color_scheme)
    
    # Add central structure on platform
    central_base = [0.8, 0.8, 0.75]
    central_color = get_color_scheme(color_scheme, central_base)
    draw_cube_manual_shading(offset_x, offset_y, platform_z + 40, 60, 60, 80, central_color)

def draw_rock_tower():
    """Draw central rock tower - SMALLER, just bigger than biggest castle"""
    x, y, z = central_rock_pos
    rock_color = [0.4, 0.4, 0.35]
    
    # Base level - bigger and taller to fill gaps
    draw_cube_manual_shading(x, y, z + 256, 352, 330, 413, rock_color)
    
    # Second level - bigger to overlap and fill gaps
    draw_cube_manual_shading(x - 15, y + 8, z + 650, 308, 286, 375, rock_color)
    
    # Third level - bigger to fill gaps
    draw_cube_manual_shading(x + 12, y - 10, z + 1006, 264, 242, 338, rock_color)
    
    # Fourth level - bigger to fill gaps
    draw_cube_manual_shading(x - 5, y + 5, z + 1300, 220, 198, 250, rock_color)
    
    # Peak - bigger to fill gaps
    draw_cube_manual_shading(x, y, z + 1488, 165, 154, 125, rock_color)

def draw_rock_tower_platform():
    """Draw simple platform on top of smaller rock tower"""
    x, y, z = central_rock_pos
    platform_height = z + 1600
    
    # Simple circular platform
    platform_radius = 120
    platform_thickness = 30
    platform_color = [0.6, 0.6, 0.55]
    
    glColor3f(platform_color[0], platform_color[1], platform_color[2])
    # Main platform disc
    draw_filled_circle(x, y, platform_height + platform_thickness/2, platform_radius)
    
    # Simple low railing around the edge
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
    """Draw spiral stairs around smaller rock tower"""
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
        
        # Support pillars every 10 steps
        if i % 10 == 0:
            draw_cube_manual_shading(0, 0, -50, 25, 25, 100, stair_color)
        
        glPopMatrix()

def draw_rope_connections():
    """Draw ropes connecting towers to castle centers and rock tower"""
    for config in castle_configs:
        pos = config['position']
        size = config['size']
        wall_height = config['wall_height']
        
        # Castle center bar positioned above the walls
        castle_center_height = pos[2] + wall_height
        castle_center = [pos[0], pos[1], castle_center_height]
        
        # Place rope support bar at castle center
        bar_height = 350
        draw_rope_support_bar(castle_center[0], castle_center[1], castle_center[2], bar_height)
        
        # Connect castle center to rock tower
        center_bar_top = [castle_center[0], castle_center[1], castle_center[2] + bar_height - 50]
        rock_platform = [central_rock_pos[0], central_rock_pos[1], central_rock_pos[2] + 1600 + 150]
        draw_rope(center_bar_top, rock_platform)
    
    # Add main support bar at rock tower
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
    
    # Color variation
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
            
            draw_stone_block(world_x, world_y, world_z, block_width,
                           thickness + 5, block_height, angle, row, col, color_scheme)
            

def draw_wooden_circle_on_roof(castle, radius=120, thickness=20):
    """Draw a wooden circular platform at the center of the castle roof."""
    x, y, z = castle['position']
    roof_z = z + castle['roof_z'] + thickness/2

    # Wooden color
    wood_color = [0.55, 0.27, 0.07]  # brownish
    
    # Draw main circular plate
    draw_filled_circle(x, y, roof_z, radius)
    
    # Optional: draw simple vertical wooden posts around the edge
    post_height = thickness
    post_size = 10
    for angle in range(0, 360, 30):
        rad = radians(angle)
        px = x + radius * cos(rad)
        py = y + radius * sin(rad)
        draw_cube_manual_shading(px, py, roof_z + post_height/2, post_size, post_size, post_height, wood_color)


def draw_castle_roof_rectangle(castle):
    """Draw a flat rectangular roof on top of the castle."""
    x, y, z = castle['position']
    half = castle['size'] / 2
    roof_z = z + castle['roof_z']  # use roof_z height from config

    glColor3f(0.7, 0.7, 0.7)  # light grey roof
    glBegin(GL_QUADS)
    glVertex3f(x - half, y - half, roof_z)
    glVertex3f(x + half, y - half, roof_z)
    glVertex3f(x + half, y + half, roof_z)
    glVertex3f(x - half, y + half, roof_z)
    glEnd()



def draw_single_castle(config):
    """Draw individual castle with hollow interior"""
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
    
    # Draw towers with platforms
    for (x, y) in corners:
        draw_tower_with_platform(x, y, pos[2], tower_radius, height, floors, color_scheme)
    
    # Draw walls
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
    
    # ADD RAILINGS ON TOP OF CASTLE WALLS
    railing_height = 80
    railing_color = get_color_scheme(color_scheme, [0.6, 0.6, 0.55])
    railing_top_z = pos[2] + wall_height + railing_height/2
    
    # Draw railings on each wall segment
    for i in range(len(corners)):
        x1, y1 = corners[i]
        x2, y2 = corners[(i + 1) % len(corners)]
        
        dx, dy = x2 - x1, y2 - y1
        length = (dx**2 + dy**2)**0.5
        
        dx_norm, dy_norm = dx / length * wall_inset, dy / length * wall_inset
        wall_x1, wall_y1 = x1 + dx_norm, y1 + dy_norm
        wall_x2, wall_y2 = x2 - dx_norm, y2 - dy_norm
        
        # Calculate railing positions along the wall
        num_railings = int(length / 100)  # One railing every 100 units
        for j in range(num_railings + 1):
            t = j / max(num_railings, 1)
            rail_x = wall_x1 + t * (wall_x2 - wall_x1)
            rail_y = wall_y1 + t * (wall_y2 - wall_y1)
            
            # Draw vertical railing post
            draw_cube_manual_shading(rail_x, rail_y, railing_top_z, 15, 15, railing_height, railing_color)
    
    # Add horizontal railing bars connecting the posts
    railing_bar_color = get_color_scheme(color_scheme, [0.65, 0.65, 0.6])
    for i in range(len(corners)):
        x1, y1 = corners[i]
        x2, y2 = corners[(i + 1) % len(corners)]
        
        dx, dy = x2 - x1, y2 - y1
        length = (dx**2 + dy**2)**0.5
        
        dx_norm, dy_norm = dx / length * wall_inset, dy / length * wall_inset
        wall_x1, wall_y1 = x1 + dx_norm, y1 + dy_norm
        wall_x2, wall_y2 = x2 - dx_norm, y2 - dy_norm
        
        # Draw horizontal railing bar
        midx = (wall_x1 + wall_x2) / 2
        midy = (wall_y1 + wall_y2) / 2
        
        glPushMatrix()
        glTranslatef(midx, midy, pos[2] + wall_height + railing_height - 20)
        angle = atan2(wall_y2 - wall_y1, wall_x2 - wall_x1) * 180 / 3.14159
        glRotatef(angle, 0, 0, 1)
        draw_cube_manual_shading(0, 0, 0, length - 2*wall_inset, 10, 8, railing_bar_color)
        glPopMatrix()
    
    # Hollow interior walls
    interior_base = [0.82, 0.8, 0.72]
    interior_color = get_color_scheme(color_scheme, interior_base)
    wall_thickness_inner = 20
    inner_length = size * 0.8
    inner_height = wall_height
    half = inner_length / 2
    
    # North wall
    draw_cube_manual_shading(pos[0], pos[1] + half - wall_thickness_inner/2,
                            pos[2] + inner_height/2,
                            inner_length, wall_thickness_inner, inner_height, interior_color)
    # South wall
    draw_cube_manual_shading(pos[0], pos[1] - half + wall_thickness_inner/2,
                            pos[2] + inner_height/2,
                            inner_length, wall_thickness_inner, inner_height, interior_color)
    # East wall
    draw_cube_manual_shading(pos[0] + half - wall_thickness_inner/2, pos[1],
                            pos[2] + inner_height/2,
                            wall_thickness_inner, inner_length, inner_height, interior_color)
    # West wall
    draw_cube_manual_shading(pos[0] - half + wall_thickness_inner/2, pos[1],
                            pos[2] + inner_height/2,
                            wall_thickness_inner, inner_length, inner_height, interior_color)
    
    # Draw gate
    gate_base = [0.3, 0.3, 0.3]
    gate_color = get_color_scheme(color_scheme, gate_base)
    draw_cube_manual_shading(pos[0], pos[1] - half + wall_inset, pos[2] + wall_height/2,
                            300, 80, wall_height, gate_color)
    

    # Draw flat rectangular roof
    draw_castle_roof_rectangle(config)

    
    # Draw wooden circle on roof
    draw_wooden_circle_on_roof(config, radius=120, thickness=20)


def draw_wooden_logs_on_largest_castle():
    """Place horizontal wooden logs at fixed coordinates on the largest castle roof."""
    # Fixed position
    x, y, z = 1200, 1500, 0
    
    quad = gluNewQuadric()
    log_radius = 40   # thick logs
    log_length = 320  # long logs
    num_logs = 5
    spacing = 5  # spacing between logs vertically

    for i in range(num_logs):
        glPushMatrix()
        # Move to base position
        glTranslatef(x, y, z + i*(log_radius*2 + spacing))
        # Rotate cylinder to lay horizontally along X-axis
        glRotatef(90, 0, 1, 0)
        glColor3f(0.55, 0.27, 0.07)  # brown wood
        gluCylinder(quad, log_radius, log_radius, log_length, 16, 16)
        glPopMatrix()


def draw_chest(x, y, z, size=250):
    """Draw a simple treasure chest near the castle wall."""
    # Chest base (brown box)
    chest_color = [0.55, 0.27, 0.07]  # wooden brown
    draw_cube_manual_shading(x, y, z + size/4, size, size*0.6, size/2, chest_color)

    # Chest lid (slightly curved top)
    lid_color = [0.45, 0.2, 0.05]
    draw_cube_manual_shading(x, y, z + size*0.75, size, size*0.6, size/3, lid_color)

    # Golden lock plate
    lock_color = [1.0, 0.84, 0.0]  # gold
    draw_cube_manual_shading(x, y + size*0.3, z + size*0.5, size*0.2, size*0.05, size*0.2, lock_color)


def draw_circle_flat(x, y, z, radius, color=[0.55, 0.27, 0.07], segments=64):
    """Draw a flat circle at (x, y, z) with specified color."""
    glColor3f(*color)
    glBegin(GL_TRIANGLE_FAN)
    glVertex3f(x, y, z)
    for i in range(segments + 1):
        angle = 2 * 3.14159 * i / segments
        dx = radius * cos(angle)
        dy = radius * sin(angle)
        glVertex3f(x + dx, y + dy, z)
    glEnd()


def draw_all_structures():
    """Draw complete castle complex with chests, logs, and teleport circles."""
    TELEPORT_RADIUS = 120
    WOOD_THICKNESS = 20

    # Individual castles
    for config in castle_configs:
        draw_single_castle(config)

        # 🔹 Draw chest if this castle has one
        if config.get('chest'):
            chest = config['chest']
            draw_chest(chest['position'][0],
                       chest['position'][1],
                       chest['position'][2])

        # 🔹 Draw teleport circle at roof (wooden circle)
        cx, cy, cz = config['position']
        roof_z = cz + config['roof_z']
        draw_circle_flat(cx, cy, roof_z + 15, TELEPORT_RADIUS, color=[0.55, 0.27, 0.07])


        # 🔹 Draw teleport circle at bottom of castle
        draw_circle_flat(cx, cy, cz + 2, TELEPORT_RADIUS, color=[1.0, 1.0, 1.0])  # white

    # Wooden logs on largest castle
    draw_wooden_logs_on_largest_castle()

    # Central rock tower with platform
    draw_rock_tower()
    draw_rock_tower_platform()
    draw_spiral_stairs_around_rock()

    # Rope connections
    draw_rope_connections()

    # Perimeter wall (excludes largest castle)
    draw_perimeter_wall()

    # Draw player if not in FPP
    if not fpp_mode:
        draw_human(player_pos[0], player_pos[1], player_pos[2], scale=60)




def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    """Draw text on screen"""
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

def is_player_on_chest(player_pos, chest):
    px, py, pz = player_pos
    cx, cy, cz = 1200,500,0
    distance_threshold = chest['size'] / 2 + 20

    dx = abs(px - cx)
    dy = abs(py - cy)
    dz = abs(pz - cz)

    return dx <= distance_threshold and dy <= distance_threshold and dz <= distance_threshold

def is_player_on_wooden_logs(player_pos):
    """Check if player is close enough to the wooden logs to collect arrows."""
    px, py, pz = player_pos
    log_x, log_y, log_z = 1200, 1500, 0
    distance_threshold = 200  # allowable distance to pick up logs

    dx = px - log_x
    dy = py - log_y
    dz = pz - log_z

    distance = (dx**2 + dy**2 + dz**2)**0.5
    return distance <= distance_threshold



def clamp_player_position():
    """Clamp player inside allowed zones so he cannot cross boundaries."""
    global player_pos
    x, y, z = player_pos

    # Find castles where player is within Z range
    valid_castles = []
    for castle in castle_configs:
        z_min = castle['position'][2]
        z_max = castle['position'][2] + castle['height']
        if z_min <= z <= z_max:
            valid_castles.append(castle)

    if valid_castles:
        # Choose the castle closest to player in XY plane
        closest_castle = min(valid_castles,
                             key=lambda c: (x - c['position'][0])**2 + (y - c['position'][1])**2)
        half = closest_castle['size'] / 2
        x_min, x_max = closest_castle['position'][0] - half, closest_castle['position'][0] + half
        y_min, y_max = closest_castle['position'][1] - half, closest_castle['position'][1] + half
        player_pos[0] = max(x_min, min(x, x_max))
        player_pos[1] = max(y_min, min(y, y_max))
        return

    # Central rock platform
    rock_x, rock_y, rock_z = central_rock_pos
    rock_radius = 220
    rock_height = 1600 + 150
    if rock_z <= z <= rock_z + rock_height:
        player_pos[0] = max(rock_x - rock_radius, min(x, rock_x + rock_radius))
        player_pos[1] = max(rock_y - rock_radius, min(y, rock_y + rock_radius))
        return

    # Perimeter guard tower area (approx)
    min_x = min([c['position'][0] - c['size']/2 for c in castle_configs]) - 500
    max_x = max([c['position'][0] + c['size']/2 for c in castle_configs]) + 500
    min_y = min([c['position'][1] - c['size']/2 for c in castle_configs]) - 500
    max_y = max([c['position'][1] + c['size']/2 for c in castle_configs]) + 500
    if 0 <= z <= 600:
        player_pos[0] = max(min_x, min(x, max_x))
        player_pos[1] = max(min_y, min(y, max_y))
        return
    

def heal_castle():
    global player_coins, castle_health, max_castle_health

    COST = 50
    HEAL_AMOUNT = 20

    if player_coins >= COST and castle_health < max_castle_health:
        player_coins -= COST
        castle_health = min(max_castle_health, castle_health + HEAL_AMOUNT)
        print(f"Castle healed by {HEAL_AMOUNT}! Health = {castle_health}, Coins left = {player_coins}")
    else:
        print("Not enough coins or castle already at max health.")

    


def setup_camera():
    global fpp_mode
    """Setup camera perspective"""
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    
    # Slightly wider FOV for FPP
    fov = 70 if fpp_mode else fovY
    gluPerspective(fov, 1.25, 1.0, 30000)  # near plane 1.0 for FPP
    
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    
    if fpp_mode:
        # Place camera slightly above player so you're not inside the model
        eye_x, eye_y, eye_z = player_pos
        eye_z += 120  # adjust based on player model height
        rad = radians(player_angle + 90)
        look_x = eye_x + cos(rad) * 5 # look a bit forward
        look_y = eye_y + sin(rad) * 5
        look_z = eye_z
        gluLookAt(eye_x, eye_y, eye_z, look_x, look_y, look_z, 0, 0, 1)

    else:
        # Orbiting camera around player/scene center using camera_pos
        eye_x, eye_y, eye_z = camera_pos
        center_x, center_y, center_z = -1000, 0, 600  # target point
        gluLookAt(eye_x, eye_y, eye_z, center_x, center_y, center_z, 0, 0, 1)




def show_screen():
    """Main display function"""
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, 1000, 800)
    setup_camera()
    
    # Draw multi-colored grid floor with various green shades
    # draw_multi_colored_grid()
    
    # Draw structures
    draw_all_structures()
    # Draw minimal vegetation (15 trees + 25 bushes)
    
    # Display info
    draw_text(10, 770, f"Coins: {player_coins}", GLUT_BITMAP_HELVETICA_18)
    draw_text(10, 740, f"Arrows: {player_arrows}", GLUT_BITMAP_HELVETICA_18)
    draw_text(10, 710, f"Castle Health: {castle_health}", GLUT_BITMAP_HELVETICA_18)

    # draw_text(10, 770, f"Castle Complex with Perimeter Wall - {len(castle_configs)} Castles")
    # draw_text(10, 740, "Controls: Arrows=Rotate, Z/X=Zoom")
    # draw_text(10, 710, f"Camera Distance: {int(cam_dist)}")
    # draw_text(10, 680, "Perimeter wall excludes biggest castle")
    
    glutSwapBuffers()

def handle_special_keys(key, x, y):
    global cam_angle_h, camera_radius, camera_height, camera_pos

    angle_step = radians(2)
    height_step = 100

    if key == GLUT_KEY_LEFT:
        cam_angle_h += angle_step
    elif key == GLUT_KEY_RIGHT:
        cam_angle_h -= angle_step
    elif key == GLUT_KEY_UP:
        camera_height += height_step
    elif key == GLUT_KEY_DOWN:
        camera_height = max(0, camera_height - height_step)  # clamp at ground level

    # Update camera position
    camera_pos[0] = camera_radius * cos(cam_angle_h)
    camera_pos[1] = camera_radius * sin(cam_angle_h)
    camera_pos[2] = camera_height

    glutPostRedisplay()




def handle_mouse_button(button, state, x, y):

    global fpp_mode
    
    if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        fpp_mode = not fpp_mode
        if fpp_mode:
            print("FPP mode activated via RMB")
        else:
            print("FPP mode deactivated via RMB")


def handle_keyboard(key, x, y):
    """Keyboard input: camera, movement, rotation, teleport, with boundary clamping."""
    global cam_dist, player_pos, player_angle, player_speed, player_turn_speed, player_coins, last_chest_time, player_arrows, camera_radius, min_radius, max_radius 
    k = key.decode("utf-8").lower()
    zoom_step = 200

    # Camera zoom
    if k == 'z':
        camera_radius = max(min_radius, camera_radius - zoom_step)
    elif k == 'x':
        camera_radius = min(max_radius, camera_radius + zoom_step)

    camera_pos[0] = camera_radius * cos(cam_angle_h)
    camera_pos[1] = camera_radius * sin(cam_angle_h)

    
    glutPostRedisplay()

    # Player rotation
    if k == 'a':
        player_angle += player_turn_speed
    elif k == 'd':
        player_angle -= player_turn_speed

    # Move player forward/backward
    elif k == 'w':
        if player_pos != [central_rock_pos[0], central_rock_pos[1], central_rock_pos[2] + 1630]:
            rad = radians(player_angle + 90)
            player_pos[0] += player_speed * cos(rad)
            player_pos[1] += player_speed * sin(rad)
            clamp_player_position()
    elif k == 's':
        if player_pos != [central_rock_pos[0], central_rock_pos[1], central_rock_pos[2] + 1630]:
            rad = radians(player_angle + 90)
            player_pos[0] -= player_speed * cos(rad)
            player_pos[1] -= player_speed * sin(rad)
            clamp_player_position()
    elif k == 'f':
        print(player_pos)
        current_time = time.time()
        if current_time - last_chest_time >= CHEST_COOLDOWN:
            for config in castle_configs:
                chest = config.get('chest')
                if chest and is_player_on_chest(player_pos, chest):
                    player_coins += 100
                    last_chest_time = current_time
                    print(f"Collected 100 coins! Total coins: {player_coins}")
                    break
        else:
            print("Chest is recharging... wait a few seconds.")

        if is_player_on_wooden_logs(player_pos):
            player_arrows += 100
            print(f"Collected arrows! Total: {player_arrows}")

    # Teleport to castle roofs
    elif k in ['1', '2', '3']:
        if player_pos == [central_rock_pos[0], central_rock_pos[1], central_rock_pos[2] + 1630]:
            index = int(k) - 1
            castle = castle_configs[index]
            # Teleport player above castle roof
            player_pos[0] = castle['position'][0]
            player_pos[1] = castle['position'][1]
            player_pos[2] = castle['position'][2] + castle['roof_z'] + 75

            # Clamp only within the castle just teleported
            half = castle['size'] / 2
            player_pos[0] = max(castle['position'][0]-half, min(player_pos[0], castle['position'][0]+half))
            player_pos[1] = max(castle['position'][1]-half, min(player_pos[1], castle['position'][1]+half))

            glutPostRedisplay()
            return


    elif key == b'4':  # teleport back to spawn
        # distance threshold to consider "at the center" (with margin)
        CENTER_RADIUS = 150  # increased for some tolerance

        for castle in castle_configs:
            cx, cy, cz = castle['position']
            dx = player_pos[0] - cx
            dy = player_pos[1] - cy
            distance = (dx**2 + dy**2)**0.5

            if distance <= CENTER_RADIUS:
                # Teleport player to spawn
                player_pos = [central_rock_pos[0], central_rock_pos[1], central_rock_pos[2] + 1630]
                print(f"Player teleported to spawn from center of castle at {castle['position']}")
                break  # stop after teleporting

    elif k == 'e':  # teleport up or down
        TELEPORT_RADIUS = 120  # wooden circle radius
        WOOD_THICKNESS = 20    # thickness of the wooden circle

        for castle in castle_configs:
            cx, cy, cz = castle['position']
            roof_z = cz + castle['roof_z']  # top of roof/platform

            dx = player_pos[0] - cx
            dy = player_pos[1] - cy
            distance = (dx**2 + dy**2)**0.5

            # --- Teleport down from roof ---
            if distance <= TELEPORT_RADIUS and player_pos[2] >= roof_z:
                player_pos[0] = cx
                player_pos[1] = cy
                player_pos[2] = cz + 50  # slightly above ground
                print(f"Player teleported down from roof of castle at {castle['position']}")
                break

            # --- Teleport up from ground ---
            elif distance <= TELEPORT_RADIUS and abs(player_pos[2] - (cz + 50)) < 100:
                player_pos[0] = cx
                player_pos[1] = cy
                player_pos[2] = roof_z + WOOD_THICKNESS / 2
                print(f"Player teleported up to roof of castle at {castle['position']}")
                break

    elif k == 'h':
        heal_castle()






    glutPostRedisplay()




def main():
    """Main function"""
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"Castle Complex with Perimeter Wall")
    
    glEnable(GL_DEPTH_TEST)
    # glDepthFunc(GL_LESS)
    
    glutDisplayFunc(show_screen)
    glutKeyboardFunc(handle_keyboard)
    glutSpecialFunc(handle_special_keys)
    glutMouseFunc(handle_mouse_button)

    
    glutMainLoop()

if __name__ == "__main__":
    main()
