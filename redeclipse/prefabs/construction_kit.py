from redeclipse.objects import cube
import math
import random
from redeclipse.prefabs.orientations import SELF, SOUTH, NORTH, WEST, EAST, ABOVE, BELOW, VEC_ORIENT_MAP_INV
from redeclipse.prefabs.vector import FineVector, CoarseVector, AbsoluteVector

ROOM_SIZE = 8


def mv(a, b):
    return (
        a[0] + b[0],
        a[1] + b[1],
        a[2] + b[2],
    )


def mi(*args):
    if len(args) == 1:
        p0 = args[0][0]
        p1 = args[0][1]
        p2 = args[0][2]
    else:
        p0 = args[0]
        p1 = args[1]
        p2 = args[2]

    return (
        p0 * -1,
        p1 * -1,
        p2 * -1,
    )


def column_points(size, direction):
    for i in range(size):
        if direction in ('-x', '+x', 'x'):
            yield FineVector(i, 0, 0)
        elif direction in ('-y', '+y', 'y'):
            yield FineVector(0, i, 0)
        elif direction in ('-z', '+z', 'z'):
            yield FineVector(0, 0, i)


def wall_points(size, direction, limit_j=100, limit_i=100):
    if size > 0:
        i_lower_bound = 0
        i_upper_bound = size
    else:
        i_lower_bound = size
        i_upper_bound = 0

    for i in range(i_lower_bound, i_upper_bound):
        # Allow partial_j walls
        if i > limit_i:
            continue

        if size > 0:
            j_lower_bound = 0
            j_upper_bound = size
        else:
            j_lower_bound = size
            j_upper_bound = 0

        for j in range(j_lower_bound, j_upper_bound):
            # Allow partial_j walls
            if j > limit_j:
                continue

            if direction == '-z':
                yield FineVector(i, j, 0)
            elif direction == '+z':
                yield FineVector(i, j, size - 1)
            elif direction == '-y':
                yield FineVector(i, 0, j)
            elif direction == '+y':
                yield FineVector(i, size - 1, j)
            elif direction == '-x':
                yield FineVector(0, i, j)
            elif direction == '+x':
                yield FineVector(size - 1, i, j)


def multi_wall(world, directions, size, pos, tex=2):
    for direction in directions:
        wall(world, direction, size, pos, tex=tex)


def wall(world, direction, size, pos, tex=2):
    for point in wall_points(size, direction):
        world.set_point(
            *mv(point, pos),
            cube.newtexcube(tex=tex)
        )

class ConstructionKitMixin(object):

    def x_column(self, world, offset, direction, length, tex=2):
        offset = offset.rotate(self.orientation)
        adjustment = self.x_get_adjustment()
        local_position = self.pos + offset + adjustment
        # Then get the orientation, rotated, and converted to ±xyz
        orient = VEC_ORIENT_MAP_INV[direction.rotate(self.orientation)]
        for point in column_points(length, orient):
            world.set_pointv(
                point + local_position,
                cube.newtexcube(tex=tex)
            )

    def x_ceiling(self, world, offset, tex=2, size=ROOM_SIZE):
        return self.x_rectangular_prism(world, offset + FineVector(0, 0, 7), AbsoluteVector(size, size, 1), tex=tex)

    def x_floor(self, world, offset, tex=2, size=ROOM_SIZE):
        return self.x_rectangular_prism(world, offset, AbsoluteVector(size, size, 1), tex=tex)

    def x_wall(self, world, offset, face, tex=2):
        offset = offset.rotate(self.orientation)
        local_position = self.pos + offset
        real_face = self.x_get_face(face)
        # print('face %s => orientation %s => real_face %s' % (face, self.orientation, real_face))

        for point in wall_points(ROOM_SIZE, real_face):
            world.set_pointv(
                point + local_position,
                cube.newtexcube(tex=tex)
            )

    def x_get_adjustment(self):
        if self.orientation == '+x':
            return CoarseVector(0, 0, 0)
        elif self.orientation == '-x':
            return CoarseVector(1, 1, 0)
        elif self.orientation == '+y':
            return CoarseVector(1, 0, 0)
        elif self.orientation == '-y':
            return CoarseVector(0, 1, 0)

    def x_ring(self, world, offset, size, tex=2):
        # world, FineVector(-2, -2, i), 12, tex=accent_tex)
        self.x_rectangular_prism(world, offset, AbsoluteVector(1, size - 1, 1), tex=tex)
        self.x_rectangular_prism(world, offset, AbsoluteVector(size - 1, 1, 1), tex=tex)
        self.x_rectangular_prism(world, offset + FineVector(0, size - 1, 0), AbsoluteVector(size, 1, 1), tex=tex)
        self.x_rectangular_prism(world, offset + FineVector(size - 1, 0, 0), AbsoluteVector(1, size, 1), tex=tex)

    def x_rectangular_prism(self, world, offset, xyz, tex=2, subtract=False):
        offset = offset.rotate(self.orientation)
        xyz = xyz.rotate(self.orientation)
        # We need to offset self.pos with an adjustment vector. Because
        # reasons. Awful awful reasons.
        adjustment = self.x_get_adjustment()

        local_position = self.pos + adjustment + offset
        print('self', self.pos.fine(), 'off', offset.fine(),
              'locl', local_position.fine(), 'dims', xyz)

        for point in cube_points(xyz.x, xyz.y, xyz.z):
            if subtract:
                world.del_pointv(
                    point + local_position
                )
            else:
                world.set_pointv(
                    point + local_position,
                    cube.newtexcube(tex=tex)
                )

    def x_low_wall(self, world, offset, face, tex=2):
        offset = offset.rotate(self.orientation)
        local_position = self.pos + offset
        real_face = self.x_get_face(face)

        for point in wall_points(ROOM_SIZE, real_face, limit_j=2):
            if point.z == 0:
                print('\t>', point + local_position)
            world.set_pointv(
                point + local_position,
                cube.newtexcube(tex=tex)
            )

    def x_get_face(self, face):
        if self.orientation == '+x':
            if face == NORTH:
                return '-x'
            elif face == SOUTH:
                return '+x'
            elif face == EAST:
                return '+y'
            elif face == WEST:
                return '-y'
        elif self.orientation == '-x':
            if face == NORTH:
                return '+x'
            elif face == SOUTH:
                return '-x'
            elif face == EAST:
                return '-y'
            elif face == WEST:
                return '+y'
        elif self.orientation == '+y':
            if face == NORTH:
                return '-y'
            elif face == SOUTH:
                return '+y'
            elif face == EAST:
                return '+x'
            elif face == WEST:
                return '-x'
        elif self.orientation == '-y':
            if face == NORTH:
                return '+y'
            elif face == SOUTH:
                return '-y'
            elif face == EAST:
                return '-x'
            elif face == WEST:
                return '+x'
        else:
            raise Exception()

def faded_wall(world, direction, size, pos, tex=2, prob=0.7):
    for point in wall_points(size, direction):
        if random.random() < prob:
            world.set_point(
                *mv(point, pos),
                cube.newtexcube(tex=tex)
            )


def low_wall(world, direction, size, pos, height=2, tex=2):
    for point in wall_points(size, direction, limit_j=height):
        world.set_point(
            *mv(point, pos),
            cube.newtexcube(tex=tex)
        )


def column(world, direction, size, pos, tex=2, subtract=False):
    for point in column_points(size, direction):
        if subtract:
            world.del_point(
                *mv(point, pos)
            )
        else:
            world.set_point(
                *mv(point, pos),
                cube.newtexcube(tex=tex)
            )


def cube_points(x, y, z):
    """
    call with a single number for a cube, or x, y, z for a rectangular prism
    """
    if x > 0:
        x_lower_bound = 0
        x_upper_bound = x
    else:
        x_lower_bound = x
        x_upper_bound = 0

    if y > 0:
        y_lower_bound = 0
        y_upper_bound = y
    else:
        y_lower_bound = y
        y_upper_bound = 0

    if z > 0:
        z_lower_bound = 0
        z_upper_bound = z
    else:
        z_lower_bound = z
        z_upper_bound = 0

    for i in range(x_lower_bound, x_upper_bound):
        for j in range(y_lower_bound, y_upper_bound):
            for k in range(z_lower_bound, z_upper_bound):
                yield FineVector(i, j, k)


def cube_s(world, size, pos, tex=2):
    for point in cube_points(size, size, size):
        world.set_point(
            *mv(point, pos),
            cube.newtexcube(tex=tex)
        )


def rectangular_prism(world, x, y, z, pos, tex=2):
    for point in cube_points(x, y, z):
        world.set_point(
            *mv(point, pos),
            cube.newtexcube(tex=tex)
        )


def slope(world, pos, corners_down=None, tex=2):
    # Broken
    c = cube.newtexcube(tex=tex)

    if 0 in corners_down:
        c.edges[4] = 136
    if 1 in corners_down:
        c.edges[5] = 136
    if 2 in corners_down:
        c.edges[7] = 136
    if 3 in corners_down:
        c.edges[10] = 136

    world.set_point(*pos, c)


def ring(world, pos, size=8, tex=2, thickness=1):
    for point in wall_points(size, '-z'):
        if point[0] < thickness or point[0] >= size - thickness or \
                point[1] < thickness or point[1] >= size - thickness:
            world.set_point(
                *mv(point, pos),
                cube.newtexcube(tex=tex)
            )

def rotate(position, orientation):
    (x, y, z) = position
    if orientation == '-x':
        return (x, y, z)
    elif orientation == '+x':
        return (-x, y, z)
    elif orientation == '-y':
        return (y, x, z)
    elif orientation == '+y':
        return (y, -x, z)
    else:
        raise Exception("Unknown Orientation")


def rotate_a(direction, orientation):
    if orientation == '-x':
        return direction + 0 % 360
    elif orientation == '+x':
        return direction + 180 % 360
    elif orientation == '-y':
        return direction + 90 % 360
    elif orientation == '+y':
        return direction + 270 % 360
    else:
        raise Exception("Unknown Orientation")
