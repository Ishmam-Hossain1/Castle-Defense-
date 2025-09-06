from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from math import sin, cos, atan2, radians, sqrt

GRID_LENGTH = 500
cam_angle_h = 45
cam_angle_v = 30
cam_dist = 4000  # Increased for better view of perimeter wall
fovY = 60

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
        'position': [900, 1000, 0],    # Biggest castle - EXCLUDED from wall
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

# Central rock tower position
central_rock_pos = [-1000, 1500, 0]

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
    
    # Face colors with different brightness
    top_color = [min(1.0, c * 1.3) for c in base_color]
    front_color = base_color
    side_color = [c * 0.7 for c in base_color]
    back_color = [c * 0.5 for c in base_color]
    
    glBegin(GL_QUADS)
    
    # Top face (brightest)
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
    
    # Interior and gate (unchanged)
    interior_base = [0.82, 0.8, 0.72]
    gate_base = [0.3, 0.3, 0.3]
    interior_color = get_color_scheme(color_scheme, interior_base)
    gate_color = get_color_scheme(color_scheme, gate_base)
    
    draw_cube_manual_shading(pos[0], pos[1], pos[2] + wall_height/2,
                           size * 0.8, size * 0.8, wall_height, interior_color)
    draw_cube_manual_shading(pos[0], pos[1] - half_size + wall_inset, pos[2] + wall_height/2,
                           300, 80, wall_height, gate_color)


def draw_all_structures():
    """Draw complete castle complex"""
    # Individual castles
    for config in castle_configs:
        draw_single_castle(config)
    
    # Central rock tower with platform
    draw_rock_tower()
    draw_rock_tower_platform()
    draw_spiral_stairs_around_rock()
    
    # Rope connections
    draw_rope_connections()
    
    # PERIMETER WALL - encapsulates everything except biggest castle
    draw_perimeter_wall()

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
    
    gluLookAt(eye_x, eye_y, eye_z, -1000, 0, 600, 0, 0, 1)

def show_screen():
    """Main display function"""
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, 1000, 800)
    setup_camera()
    
    # Draw larger ground
    glColor3f(0.2, 0.6, 0.2)
    glBegin(GL_QUADS)
    glVertex3f(-GRID_LENGTH*20, GRID_LENGTH*20, 0)
    glVertex3f(GRID_LENGTH*20, GRID_LENGTH*20, 0)
    glVertex3f(GRID_LENGTH*20, -GRID_LENGTH*20, 0)
    glVertex3f(-GRID_LENGTH*20, -GRID_LENGTH*20, 0)
    glEnd()
    
    # Draw structures
    draw_all_structures()
    
    # Display info
    draw_text(10, 770, f"Castle Complex with Perimeter Wall - {len(castle_configs)} Castles")
    draw_text(10, 740, "Controls: Arrows=Rotate, Z/X=Zoom")
    draw_text(10, 710, f"Camera Distance: {int(cam_dist)}")
    draw_text(10, 680, "Perimeter wall excludes biggest castle")
    
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

def handle_keyboard(key, x, y):
    """Handle keyboard input"""
    global cam_dist
    if key == b'z':
        cam_dist = max(1000, cam_dist - 150)
    elif key == b'x':
        cam_dist = min(25000, cam_dist + 150)
    glutPostRedisplay()

def main():
    """Main function"""
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"Castle Complex with Perimeter Wall")
    
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LESS)
    
    glutDisplayFunc(show_screen)
    glutKeyboardFunc(handle_keyboard)
    glutSpecialFunc(handle_special_keys)
    
    glutMainLoop()

if __name__ == "__main__":
    main()
