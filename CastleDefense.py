from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from math import sin, cos, atan2, radians

# Camera variables
cam_angle_h = 45     # horizontal rotation angle (Y-axis)
cam_angle_v = 30     # vertical rotation angle (X-axis)
cam_dist = 2500      # farther back since castle is larger
fovY = 60

def draw_ground():
    glColor3f(0.2, 0.6, 0.2)  # grassy green
    glBegin(GL_QUADS)
    glVertex3f(-10000, -10000, 0)
    glVertex3f(10000, -10000, 0)
    glVertex3f(10000, 10000, 0)
    glVertex3f(-10000, 10000, 0)
    glEnd()

def draw_cuboid(x, y, z, dx, dy, dz, color):
    glPushMatrix()
    glTranslatef(x, y, z)
    glScalef(dx, dy, dz)
    glColor3fv(color)
    glutSolidCube(1.0)
    glPopMatrix()

def draw_tower(x, y, radius=80, height=400):
    quad = gluNewQuadric()
    glPushMatrix()
    glTranslatef(x, y, 0)   # tower base at ground level
    glColor3f(0.82, 0.8, 0.72)  # sandy stone
    gluCylinder(quad, radius, radius, height, 32, 32)
    glPopMatrix()

    # Battlements
    top_z = height
    for angle in range(0, 360, 30):
        rad = radians(angle)
        bx = x + (radius + 20) * cos(rad)
        by = y + (radius + 20) * sin(rad)
        draw_cuboid(bx, by, top_z + 20, 30, 30, 60, (0.55, 0.55, 0.55))

def draw_wall(x1, y1, x2, y2, thickness=200, height=300):
    midx = (x1 + x2) / 2
    midy = (y1 + y2) / 2
    length = ((x2 - x1)**2 + (y2 - y1)**2) ** 0.5

    glPushMatrix()
    glTranslatef(midx, midy, height/2)
    angle = atan2(y2 - y1, x2 - x1) * 180 / 3.14159
    glRotatef(angle, 0, 0, 1)
    glScalef(length, thickness, height)
    glColor3f(0.82, 0.8, 0.72)  # wall sandy beige
    glutSolidCube(1.0)
    glPopMatrix()

    # Battlements
    num_blocks = int(length / 60)
    for i in range(num_blocks):
        bx = x1 + (i / num_blocks) * (x2 - x1)
        by = y1 + (i / num_blocks) * (y2 - y1)
        draw_cuboid(bx, by, height + 30, 30, 30, 60, (0.55, 0.55, 0.55))

def draw_castle():
    # Bigger footprint
    corners = [(400, 400), (-400, 400), (-400, -400), (400, -400)]

    # Towers
    for (x, y) in corners:
        draw_tower(x, y)

    # Outer walls
    for i in range(len(corners)):
        x1, y1 = corners[i]
        x2, y2 = corners[(i + 1) % len(corners)]
        draw_wall(x1, y1, x2, y2)

    # Fill interior with one solid cuboid to remove hollow
    inner_size = 800  # spans from -400 to 400
    draw_cuboid(0, 0, 150, inner_size, inner_size, 300, (0.82, 0.8, 0.72))  # sandy stone

    # Gate (larger to match wall height)
    draw_cuboid(0, -400, 150, 150, 40, 300, (0.3, 0.3, 0.3))



def setupCamera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, 1.25, 0.1, 20000)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    # Convert spherical camera coords to Cartesian
    eye_x = cam_dist * cos(radians(cam_angle_v)) * cos(radians(cam_angle_h))
    eye_y = cam_dist * cos(radians(cam_angle_v)) * sin(radians(cam_angle_h))
    eye_z = cam_dist * sin(radians(cam_angle_v))

    gluLookAt(eye_x, eye_y, eye_z, 0, 0, 200, 0, 0, 1)

def showScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    setupCamera()
    draw_ground()
    draw_castle()
    glutSwapBuffers()

# Keyboard & arrow control
def specialKeys(key, x, y):
    global cam_angle_h, cam_angle_v
    if key == GLUT_KEY_LEFT:
        cam_angle_h -= 5   # rotate left
    elif key == GLUT_KEY_RIGHT:
        cam_angle_h += 5   # rotate right
    elif key == GLUT_KEY_UP:
        cam_angle_v += 5   # look up
        if cam_angle_v > 89: cam_angle_v = 89  # clamp
    elif key == GLUT_KEY_DOWN:
        cam_angle_v -= 5   # look down
        if cam_angle_v < -10: cam_angle_v = -10
    glutPostRedisplay()

def keyboard(key, x, y):
    global cam_dist
    if key == b'z':   # zoom in
        cam_dist -= 50
        if cam_dist < 200:   # allow closer
            cam_dist = 200
    elif key == b'x': # zoom out
        cam_dist += 50
        if cam_dist > 10000: # allow much farther
            cam_dist = 10000
    glutPostRedisplay()

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1200, 900)
    glutCreateWindow(b"Massive Castle with Camera Control")
    glEnable(GL_DEPTH_TEST)
    glutDisplayFunc(showScreen)
    glutSpecialFunc(specialKeys)
    glutKeyboardFunc(keyboard)
    glutIdleFunc(showScreen)
    glutMainLoop()

if __name__ == "__main__":
    main()
