#  ***** GPL LICENSE BLOCK *****
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#  All rights reserved.
#  ***** GPL LICENSE BLOCK *****


# TODO:
# + break script into addon
# + Clean up workflow for filling etc.
# + Optimisations of channel masked functions / remove entirely (can isolate)
# + Add more operator options to REDO panel
# + Add shortcut to bake AO
# + Add function to set UV shells to random colors
# + Add function to bake curvature...

import bpy
import bmesh # for random color to mesh islands
import random # for random color to mesh islands
import copy # for copying data structures
from math import fmod
from bpy.props import *
from mathutils import Color, Vector, Matrix, Quaternion

# for gradient tool
from bpy_extras import view3d_utils
import bgl


bl_info = {
    "name": "Vertex Color Master",
    "author": "Andrew Palmer (with contributions from Bartosz Styperek)",
    "version": (0, 75),
    "blender": (2, 79, 0),
    "location": "Vertex Paint | View3D > Vertex Color Master",
    "description": "Tools for manipulating vertex color data.",
    "category": "Paint",
    "wiki_url": "https://github.com/andyp123/blender_vertex_color_master",
    "tracker_url": "https://github.com/andyp123/blender_vertex_color_master/issues"
}

red_id = 'R'
green_id = 'G'
blue_id = 'B'
alpha_id = 'A'

valid_channel_ids = 'RGBA'

type_vcol = 'VCOL'
type_vgroup = 'VGROUP'
type_uv = 'UV'
valid_layer_types = [type_vcol, type_vgroup, type_uv]

def channel_items(self, context):
    items = [(red_id, "R", ""), (green_id, "G", ""), (blue_id, "B", "")]

    if bpy.app.version > (2, 79, 0):
        items.append((alpha_id, "A", ""))

    return items

brush_blend_mode_items = (('MIX', "Mix", ""),
                          ('ADD', "Add", ""),
                          ('SUB', "Sub", ""),
                          ('MUL', "Multiply", ""),
                          ('BLUR', "Blur", ""),
                          ('LIGHTEN', "Lighten", ""),
                          ('DARKEN', "Darken", ""))

channel_blend_mode_items = (('ADD', "Add", ""),
                            ('SUB', "Subtract", ""),
                            ('MUL', "Multiply", ""),
                            ('DIV', "Divide", ""),
                            ('LIGHTEN', "Lighten",  ""),
                            ('DARKEN', "Darken", ""),
                            ('MIX', "Mix", ""))

 # VCM-ISO_<CHANNEL_ID>_<VCOL_ID> ex. VCM-ISO_R_Col
isolate_mode_name_prefix = 'VCM-ISO'


###############################################################################
# HELPER FUNCTIONS
###############################################################################

def posterize(value, steps):
    return round(value * steps) / steps


def remap(value, min0, max0, min1, max1):
    r0 = max0 - min0
    if r0 == 0:
        return min1
    r1 = max1 - min1
    return ((value - min0) * r1) / r0 + min1


def channel_id_to_idx(id):
    if id is red_id:
        return 0
    if id is green_id:
        return 1
    if id is blue_id:
        return 2
    if id is alpha_id:
        return 3
    # default to red
    return 0


def get_isolated_channel_ids(vcol):
    vcol_id = vcol.name
    prefix = isolate_mode_name_prefix
    prefix_len = len(prefix)

    if vcol_id.startswith(prefix) and len(vcol_id) > prefix_len + 3:
        iso_vcol_id = vcol_id[prefix_len + 3:] # get vcol id from end of string
        iso_channel_id = vcol_id[prefix_len + 1] # get channel id
        if iso_channel_id in valid_channel_ids:
            return [iso_vcol_id, iso_channel_id]

    return None


def rgb_to_luminosity(color):
    # Y = 0.299 R + 0.587 G + 0.114 B
    return color[0] * 0.299 + color[1] * 0.587 + color[2] * 0.114


def convert_rgb_to_luminosity(mesh, src_vcol, dst_vcol, dst_channel_idx, dst_all_channels=False):
    if dst_all_channels:
        for loop_index, loop in enumerate(mesh.loops):
            c = src_vcol.data[loop_index].color
            luminosity = rgb_to_luminosity(c)
            c[0] = luminosity # assigning this way will preserve alpha
            c[1] = luminosity
            c[2] = luminosity
            dst_vcol.data[loop_index].color = c
    else:
        for loop_index, loop in enumerate(mesh.loops):
            luminosity = rgb_to_luminosity(src_vcol.data[loop_index].color)
            dst_vcol.data[loop_index].color[dst_channel_idx] = luminosity


# alpha_mode
# 'OVERWRITE' - replace with copied channel value
# 'PRESERVE' - keep existing alpha value
# 'FILL' - fill alpha with 1.0
def copy_channel(mesh, src_vcol, dst_vcol, src_channel_idx, dst_channel_idx, swap=False,
                 dst_all_channels=False, alpha_mode='PRESERVE'):
    if dst_all_channels:
        color_size = len(src_vcol.data[0].color) if len(src_vcol.data) > 0 else 3
        if alpha_mode == 'OVERWRITE' or color_size < 4:
            for loop_index, loop in enumerate(mesh.loops):
                src_val = src_vcol.data[loop_index].color[src_channel_idx]
                dst_vcol.data[loop_index].color = [src_val] * color_size
        elif alpha_mode == 'FILL':
            for loop_index, loop in enumerate(mesh.loops):
                src_val = src_vcol.data[loop_index].color[src_channel_idx]
                dst_vcol.data[loop_index].color = [src_val, src_val, src_val, 1.0]
        else: # default to preserve
            for loop_index, loop in enumerate(mesh.loops):
                c = src_vcol.data[loop_index].color
                src_val = c[src_channel_idx]
                c[0] = src_val
                c[1] = src_val
                c[2] = src_val
                dst_vcol.data[loop_index].color = c
    else:
        if swap:
            for loop_index, loop in enumerate(mesh.loops):
                src_val = src_vcol.data[loop_index].color[src_channel_idx]
                dst_val = dst_vcol.data[loop_index].color[dst_channel_idx]
                dst_vcol.data[loop_index].color[dst_channel_idx] = src_val
                src_vcol.data[loop_index].color[src_channel_idx] = dst_val
        else:
            for loop_index, loop in enumerate(mesh.loops):
                dst_vcol.data[loop_index].color[dst_channel_idx] = src_vcol.data[loop_index].color[src_channel_idx]

    mesh.update()


def blend_channels(mesh, src_vcol, dst_vcol, src_channel_idx, dst_channel_idx, result_channel_idx, operation='ADD'):
    if operation == 'ADD':
        for loop_index, loop in enumerate(mesh.loops):
            val = src_vcol.data[loop_index].color[src_channel_idx] + dst_vcol.data[loop_index].color[dst_channel_idx]
            dst_vcol.data[loop_index].color[result_channel_idx] = max(0.0, min(val, 1.0))  # clamp
    elif operation == 'SUB':
        for loop_index, loop in enumerate(mesh.loops):
            val = src_vcol.data[loop_index].color[src_channel_idx] - dst_vcol.data[loop_index].color[dst_channel_idx]
            dst_vcol.data[loop_index].color[result_channel_idx] = max(0.0, min(val, 1.0))  # clamp
    elif operation == 'MUL':
        for loop_index, loop in enumerate(mesh.loops):
            val = src_vcol.data[loop_index].color[src_channel_idx] * dst_vcol.data[loop_index].color[dst_channel_idx]
            dst_vcol.data[loop_index].color[result_channel_idx] = val
    elif operation == 'DIV':
        for loop_index, loop in enumerate(mesh.loops):
            src = src_vcol.data[loop_index].color[src_channel_idx]
            dst = dst_vcol.data[loop_index].color[dst_channel_idx]
            val = 0.0 if src == 0.0 else 1.0 if dst == 0.0 else src / dst
            dst_vcol.data[loop_index].color[result_channel_idx] = val
    elif operation == 'LIGHTEN':
        for loop_index, loop in enumerate(mesh.loops):
            src = src_vcol.data[loop_index].color[src_channel_idx]
            dst = dst_vcol.data[loop_index].color[dst_channel_idx]
            dst_vcol.data[loop_index].color[result_channel_idx] = src if src > dst else dst
    elif operation == 'DARKEN':
        for loop_index, loop in enumerate(mesh.loops):
            src = src_vcol.data[loop_index].color[src_channel_idx]
            dst = dst_vcol.data[loop_index].color[dst_channel_idx]
            dst_vcol.data[loop_index].color[result_channel_idx] = src if src < dst else dst
    elif operation == 'MIX':
        for loop_index, loop in enumerate(mesh.loops):
            dst_vcol.data[loop_index].color[result_channel_idx] = src_vcol.data[loop_index].color[src_channel_idx]
    else:
        return

    mesh.update()


def uvs_to_color(mesh, src_uv, dst_vcol, dst_u_idx=0, dst_v_idx=1):
    # by default copy u->r and v->g
    # uv range is -inf, inf so use fmod to remap to 0-1
    for loop_index, loop in enumerate(mesh.loops):
        c = dst_vcol.data[loop_index].color
        uv = src_uv.data[loop_index].uv
        u = fmod(uv[0], 1.0)
        v = fmod(uv[1], 1.0)
        c[dst_u_idx] = u + 1 if u < 0 else u
        c[dst_v_idx] = v + 1 if v < 0 else v
        dst_vcol.data[loop_index].color = c

    mesh.update()


def color_to_uvs(mesh, src_vcol, dst_uv, src_u_idx=0, src_v_idx=1):
    # by default copy r->u and g->v
    for loop_index, loop in enumerate(mesh.loops):
        c = src_vcol.data[loop_index].color
        uv = [c[src_u_idx], c[src_v_idx]]
        dst_uv.data[loop_index].uv = uv

    mesh.update()


def weights_to_color(mesh, src_vgroup_idx, dst_vcol, dst_channel_idx):
    vertex_weights = [0.0] * len(mesh.vertices)

    # build list of weights for vertex indices
    for i, vert in enumerate(mesh.vertices):
        for group in vert.groups:
            if group.group == src_vgroup_idx:
                vertex_weights[i] = group.weight
                break

    # copy weights to channel of dst color layer
    for loop_index, loop in enumerate(mesh.loops):
        weight = vertex_weights[loop.vertex_index]
        dst_vcol.data[loop_index].color[dst_channel_idx] = weight

    mesh.update()


def color_to_weights(obj, src_vcol, src_channel_idx, dst_vgroup_idx):
    mesh = obj.data

    # build 2d array containing sum of color channel value, number of values
    # used to calculate average for vertex when setting weights
    vertex_values = [[0.0, 0] for i in range(0, len(mesh.vertices))]

    for loop_index, loop in enumerate(mesh.loops):
        vi = loop.vertex_index
        vertex_values[vi][0] += src_vcol.data[loop_index].color[src_channel_idx]
        vertex_values[vi][1] += 1

    # replace weights of the destination group
    group = obj.vertex_groups[dst_vgroup_idx]
    mode = 'REPLACE'

    for i in range(0, len(mesh.vertices)):
        cnt = vertex_values[i][1]
        weight = 0.0 if cnt == 0.0 else vertex_values[i][0] / cnt
        group.add([i], weight, mode)

    mesh.update()


# no channel checking. Designed to more efficiently apply a color to mesh
def quick_fill_selected(mesh, vcol, color):
    vcol_data = vcol.data
    if mesh.use_paint_mask:
        selected_faces = [face for face in mesh.polygons if face.select]
        for face in selected_faces:
            for loop_index in face.loop_indices:
                c = vcol_data[loop_index].color
                c[0] = color[0]
                c[1] = color[1]
                c[2] = color[2]
                vcol_data[loop_index].color = c
    elif mesh.use_paint_mask_vertex:
        verts = mesh.vertices
        for loop_index, loop in enumerate(mesh.loops):
            if verts[loop.vertex_index].select:
                c = vcol_data[loop_index].color
                c[0] = color[0]
                c[1] = color[1]
                c[2] = color[2]
                vcol_data[loop_index].color = c
    else: # mask == 'NONE'
        for loop_index, loop in enumerate(mesh.loops):
            c = vcol_data[loop_index].color
            c[0] = color[0]
            c[1] = color[1]
            c[2] = color[2]
            vcol_data[loop_index].color = c


def fill_selected(mesh, vcol, color, active_channels):
    if mesh.use_paint_mask:
        selected_faces = [face for face in mesh.polygons if face.select]
        for face in selected_faces:
            for loop_index in face.loop_indices:
                c = vcol.data[loop_index].color
                if red_id in active_channels:
                    c[0] = color[0]
                if green_id in active_channels:
                    c[1] = color[1]
                if blue_id in active_channels:
                    c[2] = color[2]
                if alpha_id in active_channels:
                    c[3] = color[3]
                vcol.data[loop_index].color = c
    else:
        vertex_mask = True if mesh.use_paint_mask_vertex else False
        verts = mesh.vertices

        for loop_index, loop in enumerate(mesh.loops):
            if not vertex_mask or verts[loop.vertex_index].select:
                c = vcol.data[loop_index].color
                if red_id in active_channels:
                    c[0] = color[0]
                if green_id in active_channels:
                    c[1] = color[1]
                if blue_id in active_channels:
                    c[2] = color[2]
                if alpha_id in active_channels:
                    c[3] = color[3]
                vcol.data[loop_index].color = c

    mesh.update()


def invert_selected(mesh, vcol, active_channels):
    if mesh.use_paint_mask:
        selected_faces = [face for face in mesh.polygons if face.select]
        for face in selected_faces:
            for loop_index in face.loop_indices:
                c = vcol.data[loop_index].color
                if red_id in active_channels:
                    c[0] = 1 - c[0]
                if green_id in active_channels:
                    c[1] = 1 - c[1]
                if blue_id in active_channels:
                    c[2] = 1 - c[2]
                if alpha_id in active_channels:
                    c[3] = 1 - c[3]
                vcol.data[loop_index].color = c
    else:
        vertex_mask = True if mesh.use_paint_mask_vertex else False
        verts = mesh.vertices

        for loop_index, loop in enumerate(mesh.loops):
            if not vertex_mask or verts[loop.vertex_index].select:
                c = vcol.data[loop_index].color
                if red_id in active_channels:
                    c[0] = 1 - c[0]
                if green_id in active_channels:
                    c[1] = 1 - c[1]
                if blue_id in active_channels:
                    c[2] = 1 - c[2]
                if alpha_id in active_channels:
                    c[3] = 1 - c[3]
                vcol.data[loop_index].color = c

    mesh.update()


def posterize_selected(mesh, vcol, steps, active_channels):
    if mesh.use_paint_mask:
        selected_faces = [face for face in mesh.polygons if face.select]
        for face in selected_faces:
            for loop_index in face.loop_indices:
                c = vcol.data[loop_index].color
                if red_id in active_channels:
                    c[0] = posterize(c[0], steps)
                if green_id in active_channels:
                    c[1] = posterize(c[1], steps)
                if blue_id in active_channels:
                    c[2] = posterize(c[2], steps)
                if alpha_id in active_channels:
                    c[3] = posterize(c[3], steps)
                vcol.data[loop_index].color = c
    else:
        vertex_mask = True if mesh.use_paint_mask_vertex else False
        verts = mesh.vertices

        for loop_index, loop in enumerate(mesh.loops):
            if not vertex_mask or verts[loop.vertex_index].select:
                c = vcol.data[loop_index].color
                if red_id in active_channels:
                    c[0] = posterize(c[0], steps)
                if green_id in active_channels:
                    c[1] = posterize(c[1], steps)
                if blue_id in active_channels:
                    c[2] = posterize(c[2], steps)
                if alpha_id in active_channels:
                    c[3] = posterize(c[3], steps)
                vcol.data[loop_index].color = c

    mesh.update()


def remap_selected(mesh, vcol, min0, max0, min1, max1, active_channels):
    if mesh.use_paint_mask:
        selected_faces = [face for face in mesh.polygons if face.select]
        for face in selected_faces:
            for loop_index in face.loop_indices:
                c = vcol.data[loop_index].color
                if red_id in active_channels:
                    c[0] = remap(c[0], min0, max0, min1, max1)
                if green_id in active_channels:
                    c[1] = remap(c[1], min0, max0, min1, max1)
                if blue_id in active_channels:
                    c[2] = remap(c[2], min0, max0, min1, max1)
                if alpha_id in active_channels:
                    c[3] = remap(c[3], min0, max0, min1, max1)
                vcol.data[loop_index].color = c
    else:
        vertex_mask = True if mesh.use_paint_mask_vertex else False
        verts = mesh.vertices

        for loop_index, loop in enumerate(mesh.loops):
            if not vertex_mask or verts[loop.vertex_index].select:
                c = vcol.data[loop_index].color
                if red_id in active_channels:
                    c[0] = remap(c[0], min0, max0, min1, max1)
                if green_id in active_channels:
                    c[1] = remap(c[1], min0, max0, min1, max1)
                if blue_id in active_channels:
                    c[2] = remap(c[2], min0, max0, min1, max1)
                if alpha_id in active_channels:
                    c[3] = remap(c[3], min0, max0, min1, max1)
                vcol.data[loop_index].color = c

    mesh.update()


def adjust_hsv(mesh, vcol, h_offset, s_offset, v_offset, colorize):
    if mesh.use_paint_mask:
        selected_faces = [face for face in mesh.polygons if face.select]
        for face in selected_faces:
            for loop_index in face.loop_indices:
                c = Color(vcol.data[loop_index].color[:3])
                if colorize:
                    c.h = fmod(0.5 + h_offset, 1.0)
                else:
                    c.h = fmod(1.0 + c.h + h_offset, 1.0)
                c.s = max(0.0, min(c.s + s_offset, 1.0))
                c.v = max(0.0, min(c.v + v_offset, 1.0))

                new_color = vcol.data[loop_index].color
                new_color[:3] = c
                vcol.data[loop_index].color = new_color
    else:
        vertex_mask = True if mesh.use_paint_mask_vertex else False
        verts = mesh.vertices

        for loop_index, loop in enumerate(mesh.loops):
            if not vertex_mask or verts[loop.vertex_index].select:
                c = Color(vcol.data[loop_index].color[:3])
                if colorize:
                    c.h = fmod(0.5 + h_offset, 1.0)
                else:
                    c.h = fmod(1.0 + c.h + h_offset, 1.0)
                c.s = max(0.0, min(c.s + s_offset, 1.0))
                c.v = max(0.0, min(c.v + v_offset, 1.0))

                new_color = vcol.data[loop_index].color
                new_color[:3] = c
                vcol.data[loop_index].color = new_color

    mesh.update()


def get_layer_info(context):
    settings = context.scene.vertex_color_master_settings

    d = ' ' # delimiter
    s = settings.src_vcol_id
    src_type = s[:s.find(d)]
    src_id = s[s.find(d) + 1:]

    s = settings.dst_vcol_id
    dst_type = s[:s.find(d)]
    dst_id = s[s.find(d) + 1:]

    return [src_type, src_id, dst_type, dst_id]


def get_validated_input(context, get_src, get_dst):
    settings = context.scene.vertex_color_master_settings
    obj = context.active_object
    mesh = obj.data

    rv = {}
    message = None

    layer_info = get_layer_info(context)
    src_type = layer_info[0]
    src_id = layer_info[1]
    dst_type = layer_info[2]
    dst_id = layer_info[3]

    # are these conditions actually possible?
    if message is None:
        if (src_type == type_vcol or dst_type == type_vcol) and mesh.vertex_colors is None:
            message = "Object has no vertex colors."
        if (src_type == type_vgroup or dst_type == type_vgroup) and obj.vertex_groups is None:
            message = "Object has no vertex groups."
        if (src_type == type_uv or dst_type == type_uv) and mesh.uv_layers is None:
            message = "Object has no uv layers."

    # validate src
    if get_src and message is None:
        if src_type == type_vcol:
            if src_id in mesh.vertex_colors:
                rv['src_vcol'] = mesh.vertex_colors[src_id]
                rv['src_channel_idx'] = channel_id_to_idx(settings.src_channel_id)
            else:
                message = "Src color layer is not valid."
        elif src_type == type_uv:
            if src_id in mesh.uv_layers:
                rv['src_uv'] = mesh.uv_layers[src_id]
            else:
                message = "Src UV layer is not valid."            
        else:
            src_vgroup_idx = -1
            for group in obj.vertex_groups:
                if group.name == src_id:
                    src_vgroup_idx = group.index
                    rv['src_vgroup_idx'] = src_vgroup_idx
                    break
            if src_vgroup_idx < 0:
                message = "Src vertex group is not valid."

    # validate dst
    if get_dst and message is None:
        if dst_type == type_vcol:
            if dst_id in mesh.vertex_colors:
                rv['dst_vcol'] = mesh.vertex_colors[dst_id]
                rv['dst_channel_idx'] = channel_id_to_idx(settings.dst_channel_id)
            else:
                message = "Dst color layer is not valid."
        elif dst_type == type_uv:
            if dst_id in mesh.uv_layers:
                rv['dst_uv'] = mesh.uv_layers[dst_id]
            else:
                message = "Dst UV layer is not valid." 
        else:
            dst_vgroup_idx = -1
            for group in obj.vertex_groups:
                if group.name == dst_id:
                    dst_vgroup_idx = group.index
                    rv['dst_vgroup_idx'] = dst_vgroup_idx
                    break
            if dst_vgroup_idx < 0:
                message = "Dst vertex group is not valid."

    rv['error'] = message
    return rv


###############################################################################
# MAIN OPERATOR CLASSES
###############################################################################

# For the Linear Gradient tool by Bartosz Styperek
def draw_line(self, context):
    # font_id = 0  # XXX, need to find out how best to get this.
    # draw some text
    # blf.position(font_id, 15, 30, 0)
    # blf.size(font_id, 20, 72)
    # blf.draw(font_id, "Pos " + str(self.end_point.x) + " " + str(self.end_point.y))

    # 50% alpha, 2 pixel width line
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glColor4f(0.0, 0.0, 0.0, 0.5)
    bgl.glLineWidth(2)

    bgl.glBegin(bgl.GL_LINE_STRIP)
    bgl.glVertex2i(int(self.start_point.x), int(self.start_point.y))
    bgl.glVertex2i(int(self.end_point.x), int(self.end_point.y))
    bgl.glEnd()

    # restore opengl defaults
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_BLEND)
    bgl.glColor4f(0.0, 0.0, 0.0, 1.0)


def draw_pixels(self, context):
    bgl.glEnable(bgl.GL_BLEND)

    bgl.glColor3f(1, 0, 0)
    for point in self.debugPixels:
        bgl.glPointSize(10)
        bgl.glBegin(bgl.GL_POINTS)
        bgl.glVertex3f(point[0], point[1], 0)
        bgl.glEnd()
        bgl.glDisable(bgl.GL_BLEND)
        bgl.glPointSize(1)

    bgl.glColor3f(0, 1, 0)
    bgl.glPointSize(10)
    bgl.glBegin(bgl.GL_POINTS)
    bgl.glVertex3f(self.transStart.x, self.transStart.y, 0)
    bgl.glVertex3f(self.transEnd.x, self.transEnd.y, 0)
    bgl.glEnd()
    bgl.glDisable(bgl.GL_BLEND)
    bgl.glPointSize(1)
    # restore  defaults
    bgl.glDisable(bgl.GL_BLEND)
    bgl.glColor3f(0.0, 0.0, 0.0)


# This function from a script by Bartosz Styperek with modifications by me
class VertexColorMaster_LinearGradient(bpy.types.Operator):
    """Draw a line with the mouse to paint a vertex color gradient."""
    bl_idname = "vertexcolormaster.linear_gradient"
    bl_label = "VCM Linear Gradient Tool"
    bl_description = "Paint linear vertex gradient."
    bl_options = {"REGISTER", "UNDO"}

    _line_draw_handle = None

    start_point = None
    end_point = None

    def paintVerts(self, context, start_point, end_point, start_color, end_color):
        region = context.region
        rv3d = context.region_data

        obj = context.active_object
        mesh = obj.data

        bm = bmesh.new()  # create an empty BMesh
        bm.from_mesh(mesh)  # fill it in from a Mesh
        bm.verts.ensure_lookup_table()

        # List of structures containing 3d vertex and project 2d position of vertex
        vertex_data = None # Will contain vert, and vert coordinates in 2d view space
        if mesh.use_paint_mask_vertex: # Face masking not currently supported
            vertex_data = [(v, view3d_utils.location_3d_to_region_2d(region, rv3d, obj.matrix_world * v.co)) for v in bm.verts if v.select]
        else:
            vertex_data = [(v, view3d_utils.location_3d_to_region_2d(region, rv3d, obj.matrix_world * v.co)) for v in bm.verts]

        # Vertex transformation math
        down_vector = Vector((0, -1, 0))
        direction_vector = Vector((end_point.x - start_point.x, end_point.y - start_point.y, 0)).normalized()
        rotation = direction_vector.rotation_difference(down_vector)

        translation_matrix = Matrix.Translation(Vector((-start_point.x, -start_point.y, 0)))
        inverse_translantion_matrix = translation_matrix.inverted()
        rotation_matrix = rotation.to_matrix().to_4x4()
        combinedMat = inverse_translantion_matrix * rotation_matrix * translation_matrix

        transStart = combinedMat * start_point.to_4d() # Transform drawn line : rotate it to align to horizontal line
        transEnd = combinedMat * end_point.to_4d()
        minY = transStart.y
        maxY = transEnd.y
        heightTrans = maxY - minY  # Get the height of transformed vector

        # Calculate hue, saturation and value shift for blending
        c1_hue = start_color.h
        c2_hue = end_color.h
        hue_separation = c2_hue - c1_hue
        if hue_separation > 0.5:
            hue_separation = hue_separation - 1
        elif hue_separation < -0.5:
            hue_separation = hue_separation + 1
        c1_sat = start_color.s
        sat_separation = end_color.s - c1_sat
        c1_val = start_color.v
        val_separation = end_color.v - c1_val

        color_layer = bm.loops.layers.color.active

        for data in vertex_data:
            vertex = data[0]
            vertCo4d = Vector((data[1].x, data[1].y, 0))
            transVec = combinedMat * vertCo4d

            t = abs(max(min((transVec.y - minY) / heightTrans, 1), 0))
            color = Color((1, 0, 0))
            # Hue wraps, and fmod doesn't work with negative values
            color.h = fmod(1.0 + c1_hue + hue_separation * t, 1.0) 
            color.s = c1_sat + sat_separation * t
            color.v = c1_val + val_separation * t

            if mesh.use_paint_mask: # Masking by face
                face_loops = [loop for loop in vertex.link_loops if loop.face.select] # Get only loops that belong to selected faces
            else: # Masking by verts or no masking at all
                face_loops = [loop for loop in vertex.link_loops] # Get remaining vert loops

            for loop in face_loops:
                new_color = loop[color_layer]
                new_color[:3] = color
                loop[color_layer] = new_color

        bm.to_mesh(mesh)
        bm.free()
        bpy.ops.object.mode_set(mode='VERTEX_PAINT')

    def axis_snap(self, start, end, delta):
        if start.x - delta < end.x < start.x + delta:
            return Vector((start.x, end.y))
        if start.y - delta < end.y < start.y + delta:
            return Vector((end.x, start.y))
        return end

    def modal(self, context, event):
        context.area.tag_redraw()
        delta = 20

        # TODO: Display tool information in the bar at the bottom of the screen
        # Find out how other operators do this.

        if event.type in {'RIGHTMOUSE', 'ESC'}:
            return {'CANCELLED'}
        elif event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            return {'PASS_THROUGH'} # Allow navigation

        if self._line_draw_handle is None: # Drawing has not started
            if event.type == 'LEFTMOUSE':
                self.start_point = Vector((event.mouse_region_x, event.mouse_region_y))
                self.end_point = self.start_point # To prevent drawing line to random place
                args = (self, context)
                self._line_draw_handle = bpy.types.SpaceView3D.draw_handler_add(draw_line, args, 'WINDOW', 'POST_PIXEL')
        elif event.type in {'MOUSEMOVE', 'LEFTMOUSE'}:
            # Update and constrain end point
            self.end_point = Vector((event.mouse_region_x, event.mouse_region_y))
            if event.shift:
                self.axis_snap(self.start_point, self.end_point, delta)

            if event.type == 'LEFTMOUSE': # Finish updating the line and paint the vertices
                if self.end_point == self.start_point:
                    self.report({'INFO'}, 'Draw a line by dragging in the 3D View. Esc to cancel.')
                    return {'CANCELLED'}

                bpy.types.SpaceView3D.draw_handler_remove(self._line_draw_handle, 'WINDOW')
                self._line_draw_handle = None

                # Use color gradient where supported (unless we are in isolate mode)
                start_color = Color((0, 0, 0))
                end_color = Color((1, 1, 1))
                isolate = get_isolated_channel_ids(context.active_object.data.vertex_colors.active)
                if isolate is None:
                    start_color = bpy.data.brushes['Draw'].color
                    end_color = bpy.data.brushes['Draw'].secondary_color

                self.paintVerts(context, self.start_point, self.end_point, start_color, end_color)
                return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}


# Partly based on code by Bartosz Styperek
class VertexColorMaster_RandomiseMeshIslandColors(bpy.types.Operator):
    """Assign random colors to separate mesh islands"""
    bl_idname = 'vertexcolormaster.randomise_mesh_island_colors'
    bl_label = 'VCM Randomise Mesh Island Colors'
    bl_options = {'REGISTER', 'UNDO'}

    random_seed = IntProperty(
        name="Random Seed",
        description="Seed for the randomization. Change this value to get different random colors.",
        default=1,
        min=1,
        max=1000
    )

    randomize_hue = BoolProperty(
        name="Randmize Hue",
        description="Randomize Hue",
        default=True
    )

    randomize_saturation = BoolProperty(
        name="Randmize Saturation",
        description="Randomize Saturation",
        default=False
    )

    randomize_value = BoolProperty(
        name="Randmize Value",
        description="Randomize Value",
        default=False
    )

    base_hue = FloatProperty(
        name="Hue",
        description="When not randomized, the hue will be set to this value.",
        default=0.0,
        min=0.0,
        max=1.0
    )

    base_saturation = FloatProperty(
        name="Saturation",
        description="When not randomized, the saturation will be set to this value.",
        default=1.0,
        min=0.0,
        max=1.0
    )

    base_value = FloatProperty(
        name="Value",
        description="When not randomized, the value will be set to this value.",
        default=1.0,
        min=0.0,
        max=1.0
    )

    order_based = BoolProperty(
        name="Order Based",
        description="The colors assigned will be based on the number of islands. Not truly random, but maximum color separation.",
        default=False
    )

    merge_similar = BoolProperty(
        name="Merge Similar",
        description="Use the same color for similar parts of the mesh (determined by equal face count).",
        default=False
    )

    # Use custom UI for better showing randomization parameters
    def draw(self, context):
        layout = self.layout

        layout.label("Randomization Parameters")

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(self, 'randomize_hue', "Randomize")
        row.prop(self, 'base_hue', "H", slider=True)
        row = col.row(align=True)
        row.prop(self, 'randomize_saturation', "Randomize")
        row.prop(self, 'base_saturation', "S", slider=True)
        row = col.row(align=True)
        row.prop(self, 'randomize_value', "Randomize")
        row.prop(self, 'base_value', "V", slider=True)

        layout.prop(self, 'random_seed', "Seed", slider=True)

        layout.prop(self, 'order_based')
        layout.prop(self, 'merge_similar')

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return bpy.context.object.mode == 'VERTEX_PAINT' and obj is not None and obj.type == 'MESH'

    def execute(self, context):
        mesh = context.active_object.data
        random.seed(self.random_seed)

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)

        bm = bmesh.from_edit_mesh(mesh)
        bm.faces.ensure_lookup_table()
        color_layer = bm.loops.layers.color.active

        # Find all islands in the mesh
        mesh_islands = []
        selected_faces = ([f for f in bm.faces if f.select])
        faces = selected_faces if mesh.use_paint_mask or mesh.use_paint_mask_vertex else bm.faces

        bpy.ops.mesh.select_all(action="DESELECT")

        while len(faces) > 0:
            # Select linked faces to find island
            faces[0].select_set(True)
            bpy.ops.mesh.select_linked()
            mesh_islands.append([f for f in faces if f.select])
            # Hide the island and update faces
            bpy.ops.mesh.hide(unselected=False)
            faces = [f for f in faces if not f.hide]

        bpy.ops.mesh.reveal()  

        island_colors = {} # Island face count : Random color pairs

        # Used for setting hue with order based color assignment
        separationDiff = 1.0 if len(mesh_islands) == 0 else 1.0 / len(mesh_islands)

        for index, island in enumerate(mesh_islands):
            color = Color((1, 0, 0)) # (0, 1, 1) HSV

            if self.merge_similar:
                face_count = len(island)
                if face_count in island_colors.keys():
                    color = island_colors[face_count]
                else:
                    color.h = random.random() if self.randomize_hue else self.base_hue
                    color.s = random.random() if self.randomize_saturation else self.base_saturation
                    color.v = random.random() if self.randomize_value else self.base_value
                    island_colors[face_count] = color
            else:
                if self.order_based:
                    color.h = index * separationDiff if self.randomize_hue else self.base_hue
                    color.s = index * separationDiff if self.randomize_saturation else self.base_saturation
                    color.v = index * separationDiff if self.randomize_value else self.base_value
                else:
                    color.h = random.random() if self.randomize_hue else self.base_hue
                    color.s = random.random() if self.randomize_saturation else self.base_saturation
                    color.v = random.random() if self.randomize_value else self.base_value

            for face in island:
                for loop in face.loops:
                    new_color = loop[color_layer]
                    new_color[:3] = color
                    loop[color_layer] = new_color

        # Restore selection
        for f in selected_faces:
            f.select = True

        bm.free()
        bpy.ops.object.mode_set(mode='VERTEX_PAINT', toggle=False)

        return {'FINISHED'}


class VertexColorMaster_AdjustHSV(bpy.types.Operator):
    """Adjust the Hue, Saturation and Value of the the active vertex colors"""
    bl_idname = 'vertexcolormaster.adjust_hsv'
    bl_label = 'VCM Adjust HSV'
    bl_options = {'REGISTER', 'UNDO'}

    colorize = BoolProperty(
        name="Colorize",
        description="Colorize the mesh instead of adjusting hue.",
        default=False
    )

    hue_adjust = FloatProperty(
        name="Hue",
        description="Hue adjustment.",
        default=0.0,
        min=-0.5,
        max=0.5
    )

    sat_adjust = FloatProperty(
        name="Saturation",
        description="Saturation adjustment.",
        default=0.0,
        min=-1.0,
        max=1.0
    )

    val_adjust = FloatProperty(
        name="Value",
        description="Value adjustment.",
        default=0.0,
        min=-1.0,
        max=1.0
    )

    def execute(self, context):
        settings = context.scene.vertex_color_master_settings
        mesh = context.active_object.data
        vcol = mesh.vertex_colors.active

        if vcol is None:
            self.report({'ERROR'}, "Can't modify HSV when no vertex color data exists.")
            return {'FINISHED'}

        adjust_hsv(mesh, vcol, self.hue_adjust, self.sat_adjust, self.val_adjust, self.colorize)

        return {'FINISHED'}


class VertexColorMaster_ColorToUVs(bpy.types.Operator):
    """Copy vertex color channel to UVs"""
    bl_idname = 'vertexcolormaster.color_to_uvs'
    bl_label = 'VCM Color to UVs'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return bpy.context.object.mode == 'VERTEX_PAINT' and obj is not None and obj.type == 'MESH'

    def execute(self, context):
        vi = get_validated_input(context, get_src=True, get_dst=True)

        if vi['error'] is not None:
            self.report({'ERROR'}, vi['error'])
            return {'FINISHED'}

        mesh = context.active_object.data
        u_idx = 0
        v_idx = 1
        color_to_uvs(mesh, vi['src_vcol'], vi['dst_uv'], u_idx, v_idx)

        return {'FINISHED'}


class VertexColorMaster_UVsToColor(bpy.types.Operator):
    """Copy UVs to vertex color channel"""
    bl_idname = 'vertexcolormaster.uvs_to_color'
    bl_label = 'VCM UVs to Color'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return bpy.context.object.mode == 'VERTEX_PAINT' and obj is not None and obj.type == 'MESH'

    def execute(self, context):
        vi = get_validated_input(context, get_src=True, get_dst=True)

        if vi['error'] is not None:
            self.report({'ERROR'}, vi['error'])
            return {'FINISHED'}

        mesh = context.active_object.data
        u_idx = 0
        v_idx = 1
        uvs_to_color(mesh, vi['src_uv'], vi['dst_vcol'], u_idx, v_idx)

        return {'FINISHED'}


class VertexColorMaster_ColorToWeights(bpy.types.Operator):
    """Copy vertex color channel to vertex group weights"""
    bl_idname = 'vertexcolormaster.color_to_weights'
    bl_label = 'VCM Color to Weights'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return bpy.context.object.mode == 'VERTEX_PAINT' and obj is not None and obj.type == 'MESH'

    def execute(self, context):
        vi = get_validated_input(context, get_src=True, get_dst=True)

        if vi['error'] is not None:
            self.report({'ERROR'}, vi['error'])
            return {'FINISHED'}

        obj = context.active_object
        color_to_weights(obj, vi['src_vcol'], vi['src_channel_idx'], vi['dst_vgroup_idx'])

        return {'FINISHED'}


class VertexColorMaster_WeightsToColor(bpy.types.Operator):
    """Copy vertex group weights to vertex color channel"""
    bl_idname = 'vertexcolormaster.weights_to_color'
    bl_label = 'VCM Weights to color'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return bpy.context.object.mode == 'VERTEX_PAINT' and obj is not None and obj.type == 'MESH'

    def execute(self, context):
        vi = get_validated_input(context, get_src=True, get_dst=True)

        if vi['error'] is not None:
            self.report({'ERROR'}, vi['error'])
            return {'FINISHED'}

        mesh = context.active_object.data
        weights_to_color(mesh, vi['src_vgroup_idx'],
                         vi['dst_vcol'], vi['dst_channel_idx'])

        return {'FINISHED'}


class VertexColorMaster_RgbToGrayscale(bpy.types.Operator):
    """Convert the RGB color of a vertex color layer to a grayscale value"""
    bl_idname = 'vertexcolormaster.rgb_to_grayscale'
    bl_label = 'VCM RGB to grayscale'
    bl_options = {'REGISTER', 'UNDO'}

    all_channels = bpy.props.BoolProperty(
        name="All Channels",
        default=True,
        description="Put the grayscale value into all channels of the destination."
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return bpy.context.object.mode == 'VERTEX_PAINT' and obj is not None and obj.type == 'MESH'

    def execute(self, context):
        vi = get_validated_input(context, get_src=True, get_dst=True)

        if vi['error'] is not None:
            self.report({'ERROR'}, vi['error'])
            return {'FINISHED'}

        mesh = context.active_object.data
        convert_rgb_to_luminosity(
            mesh, vi['src_vcol'], vi['dst_vcol'], vi['dst_channel_idx'], self.all_channels)

        return {'FINISHED'}


class VertexColorMaster_CopyChannel(bpy.types.Operator):
    """Copy or swap channel data from one channel to another"""
    bl_idname = 'vertexcolormaster.copy_channel'
    bl_label = 'VCM Copy channel data'
    bl_options = {'REGISTER', 'UNDO'}

    swap_channels = bpy.props.BoolProperty(
        name="Swap Channels",
        default=False,
        description="Swap source and destination channels instead of copying."
    )

    all_channels = bpy.props.BoolProperty(
        name="All Channels",
        default=False,
        description="Put the copied value into all channels of the destination."
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return bpy.context.object.mode == 'VERTEX_PAINT' and obj is not None and obj.type == 'MESH'

    def execute(self, context):
        vi = get_validated_input(context, get_src=True, get_dst=True)

        if vi['error'] is not None:
            self.report({'ERROR'}, vi['error'])
            return {'FINISHED'}

        mesh = context.active_object.data
        copy_channel(mesh, vi['src_vcol'], vi['dst_vcol'], vi['src_channel_idx'],
                     vi['dst_channel_idx'], self.swap_channels, self.all_channels)

        return {'FINISHED'}


class VertexColorMaster_BlendChannels(bpy.types.Operator):
    """Blend source and destination channels (result is saved in destination)"""
    bl_idname = 'vertexcolormaster.blend_channels'
    bl_label = 'VCM Blend Channels'
    bl_options = {'REGISTER', 'UNDO'}

    blend_mode = bpy.props.EnumProperty(
        name="Blend Mode",
        items=channel_blend_mode_items,
        description="Blending operation used when the Src and Dst channels are blended.",
        default='ADD'
    )

    result_channel_id = EnumProperty(
        name="Result Channel",
        items=channel_items,
        description="Use this channel instead of the Dst."
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return bpy.context.object.mode == 'VERTEX_PAINT' and obj is not None and obj.type == 'MESH'

    def invoke(self, context, event):
        settings = context.scene.vertex_color_master_settings
        self.result_channel = settings.dst_channel_id
        return self.execute(context)

    def execute(self, context):
        vi = get_validated_input(context, get_src=True, get_dst=True)

        if vi['error'] is not None:
            self.report({'ERROR'}, vi['error'])
            return {'FINISHED'}

        mesh = context.active_object.data
        result_channel_idx = channel_id_to_idx(self.result_channel_id)
        blend_channels(mesh, vi['src_vcol'], vi['dst_vcol'], vi['src_channel_idx'],
                       vi['dst_channel_idx'], result_channel_idx, self.blend_mode)

        return {'FINISHED'}


class VertexColorMaster_Fill(bpy.types.Operator):
    """Fill the active vertex color channel(s)"""
    bl_idname = 'vertexcolormaster.fill'
    bl_label = 'VCM Fill'
    bl_options = {'REGISTER', 'UNDO'}

    value = FloatProperty(
        name="Value",
        description="Value to fill active channel(s) with.",
        default=1.0,
        min=0.0,
        max=1.0
    )

    fill_with_color = BoolProperty(
        name="Fill with Color",
        description="Ignore active channels and fill with an RGB color",
        default=False
    )

    fill_color = FloatVectorProperty(
        name="Fill Color",
        subtype='COLOR',
        default=[1.0,1.0,1.0],
        description="Color to fill vertex color data with."
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return bpy.context.object.mode == 'VERTEX_PAINT' and obj is not None and obj.type == 'MESH'

    def execute(self, context):
        settings = context.scene.vertex_color_master_settings

        mesh = context.active_object.data
        vcol = mesh.vertex_colors.active if mesh.vertex_colors else mesh.vertex_colors.new()

        isolate_mode = get_isolated_channel_ids(vcol) is not None

        if self.fill_with_color or isolate_mode:
            active_channels = ['R', 'G', 'B']
            color = [self.value] * 4 if isolate_mode else self.fill_color
            fill_selected(mesh, vcol, color, active_channels)
        else:
            color = [self.value] * 4
            fill_selected(mesh, vcol, color, settings.active_channels)

        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.prop(self, 'value', slider=True)
        row = layout.row()
        row.prop(self, 'fill_with_color')
        if self.fill_with_color:
            row = layout.row()
            row.prop(self, 'fill_color', '')


class VertexColorMaster_Invert(bpy.types.Operator):
    """Invert active vertex color channel(s)"""
    bl_idname = 'vertexcolormaster.invert'
    bl_label = 'VCM Invert'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return bpy.context.object.mode == 'VERTEX_PAINT' and obj is not None and obj.type == 'MESH'

    def execute(self, context):
        settings = context.scene.vertex_color_master_settings

        mesh = context.active_object.data
        vcol = mesh.vertex_colors.active if mesh.vertex_colors else mesh.vertex_colors.new()
        active_channels = settings.active_channels if get_isolated_channel_ids(vcol) is None else ['R', 'G', 'B']

        invert_selected(mesh, vcol, active_channels)

        return {'FINISHED'}


class VertexColorMaster_Posterize(bpy.types.Operator):
    """Posterize active vertex color channel(s)"""
    bl_idname = 'vertexcolormaster.posterize'
    bl_label = 'VCM Posterize'
    bl_options = {'REGISTER', 'UNDO'}

    steps = bpy.props.IntProperty(
        name="Steps",
        default=2,
        min=2,
        max=256,
        description="Number of different grayscale values for posterization of active channel(s)."
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return bpy.context.object.mode == 'VERTEX_PAINT' and obj is not None and obj.type == 'MESH'

    def execute(self, context):
        settings = context.scene.vertex_color_master_settings

        # using posterize(), 2 steps -> 3 tones, but best to have 2 steps -> 2 tones
        steps = self.steps - 1

        mesh = context.active_object.data
        vcol = mesh.vertex_colors.active if mesh.vertex_colors else mesh.vertex_colors.new()
        active_channels = settings.active_channels if get_isolated_channel_ids(vcol) is None else ['R', 'G', 'B']

        posterize_selected(mesh, vcol, steps, active_channels)

        return {'FINISHED'}


class VertexColorMaster_Remap(bpy.types.Operator):
    """Remap active vertex color channel(s)"""
    bl_idname = 'vertexcolormaster.remap'
    bl_label = 'VCM Remap'
    bl_options = {'REGISTER', 'UNDO'}

    min0 = FloatProperty(
        default=0,
        min=0,
        max=1
    )

    max0 = FloatProperty(
        default=1,
        min=0,
        max=1
    )

    min1 = FloatProperty(
        default=0,
        min=0,
        max=1
    )

    max1 = FloatProperty(
        default=1,
        min=0,
        max=1
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return bpy.context.object.mode == 'VERTEX_PAINT' and obj is not None and obj.type == 'MESH'

    def execute(self, context):
        settings = context.scene.vertex_color_master_settings

        mesh = context.active_object.data
        vcol = mesh.vertex_colors.active if mesh.vertex_colors else mesh.vertex_colors.new()
        active_channels = settings.active_channels if get_isolated_channel_ids(vcol) is None else ['R', 'G', 'B']

        remap_selected(mesh, vcol, self.min0, self.max0, self.min1, self.max1, active_channels)

        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout

        layout.label("Input Range")
        layout.prop(self, 'min0', "Min", slider=True)
        layout.prop(self, 'max0', "Max", slider=True)

        layout.label("Output Range")
        layout.prop(self, 'min1', "Min", slider=True)
        layout.prop(self, 'max1', "Max", slider=True)


class VertexColorMaster_EditBrushSettings(bpy.types.Operator):
    """Set vertex paint brush settings from panel buttons"""
    bl_idname = 'vertexcolormaster.edit_brush_settings'
    bl_label = 'VCM Edit Brush Settings'
    bl_options = {'REGISTER', 'UNDO'}

    blend_mode = EnumProperty(
        name='Blend Mode',
        default='MIX',
        items=brush_blend_mode_items,
        description="Blending method to use when painting with the brush."
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return bpy.context.object.mode == 'VERTEX_PAINT' and obj is not None and obj.type == 'MESH'

    def execute(self, context):
        brush = bpy.data.brushes['Draw']
        brush.vertex_tool = self.blend_mode

        return {'FINISHED'}


class VertexColorMaster_QuickFill(bpy.types.Operator):
    """Quick fill vertex color RGB with current brush color. Can use selection mask."""
    bl_idname = 'vertexcolormaster.quick_fill'
    bl_label = 'VCM Fill Color'
    bl_options = {'REGISTER', 'UNDO'}

    fill_color = FloatVectorProperty(
        name="Fill Color",
        subtype='COLOR',
        default=[1.0,1.0,1.0],
        description="Color to fill vertex color data with."
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return bpy.context.object.mode == 'VERTEX_PAINT' and obj is not None and obj.type == 'MESH'

    def execute(self, context):
        settings = context.scene.vertex_color_master_settings

        mesh = context.active_object.data
        vcol = mesh.vertex_colors.active if mesh.vertex_colors else mesh.vertex_colors.new()

        quick_fill_selected(mesh, vcol, self.fill_color)

        return {'FINISHED'}


class VertexColorMaster_IsolateChannel(bpy.types.Operator):
    """Isolate a specific channel to paint in grayscale."""
    bl_idname = 'vertexcolormaster.isolate_channel'
    bl_label = 'VCM Isolate Channel'
    bl_options = {'REGISTER', 'UNDO'}

    src_channel_id = EnumProperty(
        name="Source Channel",
        items=channel_items,
        description="Source (Src) color channel."
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return bpy.context.object.mode == 'VERTEX_PAINT' and obj is not None and obj.type == 'MESH'

    def execute(self, context):
        settings = context.scene.vertex_color_master_settings
        obj = context.active_object
        mesh = obj.data

        if mesh.vertex_colors is None:
            self.report({'ERROR'}, "Mesh has no vertex color layer to isolate.")
            return {'FINISHED'}

        # get the vcol and channel to isolate
        # create empty vcol using name template
        vcol = mesh.vertex_colors.active
        iso_vcol_id = "{0}_{1}_{2}".format(isolate_mode_name_prefix, self.src_channel_id, vcol.name)
        if iso_vcol_id in mesh.vertex_colors:
            error = "{0} Channel has already been isolated to {1}. Apply or Discard before isolating again.".format(self.src_channel_id, iso_vcol_id)
            self.report({'ERROR'}, error)
            return {'FINISHED'}

        iso_vcol = mesh.vertex_colors.new()
        iso_vcol.name = iso_vcol_id
        channel_idx = channel_id_to_idx(self.src_channel_id)

        copy_channel(mesh, vcol, iso_vcol, channel_idx, channel_idx, dst_all_channels=True, alpha_mode='FILL')
        mesh.vertex_colors.active = iso_vcol
        brush = bpy.data.brushes['Draw']
        settings.brush_color = brush.color
        brush.color = [settings.brush_value_isolate] * 3

        return {'FINISHED'}


class VertexColorMaster_ApplyIsolatedChannel(bpy.types.Operator):
    """Apply isolated channel back to the vertex color layer it came from"""
    bl_idname = 'vertexcolormaster.apply_isolated'
    bl_label = "VCM Apply Isolated Channel"
    bl_options = {'REGISTER', 'UNDO'}

    discard = BoolProperty(
        name="Discard Changes",
        default=False,
        description="Discard changes to the isolated channel instead of applying them."
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is not None and obj.type == 'MESH' and obj.data.vertex_colors is not None:
            vcol = obj.data.vertex_colors.active
            # operator will not work if the active vcol name doesn't match the right template
            vcol_info = get_isolated_channel_ids(vcol)
            return vcol_info is not None

    def execute(self, context):
        settings = context.scene.vertex_color_master_settings
        mesh = context.active_object.data

        iso_vcol = mesh.vertex_colors.active

        brush = bpy.data.brushes['Draw']
        brush.color = settings.brush_color
        settings.update_brush_value(context)

        if self.discard:
            mesh.vertex_colors.remove(iso_vcol)
            return {'FINISHED'}

        vcol_info = get_isolated_channel_ids(iso_vcol)

        vcol = mesh.vertex_colors[vcol_info[0]]
        channel_idx = channel_id_to_idx(vcol_info[1])

        if vcol is None:
            error = "Mesh has no vertex color layer named '{0}'. Was it renamed or deleted?".format(vcol_info[0])
            self.report({'ERROR'}, error)
            return {'FINISHED'}

        # assuming iso_vcol has only grayscale data, RGB are equal, so copy from R
        copy_channel(mesh, iso_vcol, vcol, 0, channel_idx)
        mesh.vertex_colors.active = vcol
        mesh.vertex_colors.remove(iso_vcol)

        return {'FINISHED'}


# TODO: Remove this once 2.79.1 is released. 2.79.0 compatibility function.
# replace in UI with paint.brush_colors_flip
class VertexColorMaster_FlipBrushColors(bpy.types.Operator):
    """Toggle foreground and background brush colors."""
    bl_idname = 'vertexcolormaster.brush_colors_flip'
    bl_label = "VCM Flip Brush Colors"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        brush = bpy.data.brushes['Draw']
        color = Color(brush.color)
        brush.color = brush.secondary_color
        brush.secondary_color = color

        return {'FINISHED'}

###############################################################################
# MAIN CLASS, UI, SETTINGS, PREFS AND REGISTRATION
###############################################################################

class VertexColorMasterProperties(bpy.types.PropertyGroup):

    def update_active_channels(self, context):
        if not self.match_brush_to_active_channels:
            return None

        active_channels = self.active_channels
        brush_value = self.brush_value

        # set draw color based on mask
        draw_color = [0.0, 0.0, 0.0]
        if red_id in active_channels:
            draw_color[0] = brush_value
        if green_id in active_channels:
            draw_color[1] = brush_value
        if blue_id in active_channels:
            draw_color[2] = brush_value

        bpy.data.brushes['Draw'].color = draw_color

        return None

    active_channels = EnumProperty(
        name="Active Channels",
        options={'ENUM_FLAG'},
        items=channel_items,
        description="Which channels to enable.",
        # default={'R', 'G', 'B'},
        update=update_active_channels # TODO: Remove this once Blender 2.79.1 is out
    )

    match_brush_to_active_channels = BoolProperty(
        name="Match Active Channels",
        default=True,
        description="Change the brush color to match the active channels.",
        update=update_active_channels
    )

    def update_brush_value(self, context):
        if self.match_brush_to_active_channels:
            return self.update_active_channels(context)

        brush = bpy.data.brushes['Draw']
        color = Color(brush.color)
        color.v = self.brush_value
        brush.color = color

        return None

    def update_brush_value_isolate(self, context):
        brush = bpy.data.brushes['Draw']
        color = Color(brush.color)
        color.s = 0.0
        color.v = self.brush_value_isolate
        brush.color = color

        return None

    # Used only to store the color between RGBA and isolate modes
    brush_color = FloatVectorProperty(
        name="Brush Color",
        description="Color of the brush.",
        default=(1, 0, 0)
    )

    brush_value = FloatProperty(
        name="Brush Value",
        description="Value of the brush color.",
        default=1.0,
        min=0.0,
        max=1.0,
        update=update_brush_value
    )

    brush_value_isolate = FloatProperty(
        name="Brush Value",
        description="Value of the brush color.",
        default=1.0,
        min=0.0,
        max=1.0,
        update=update_brush_value_isolate
    )


    def vcol_layer_items(self, context):
        obj = context.active_object
        mesh = obj.data

        items = [] if mesh.vertex_colors is None else [
            ("{0} {1}".format(type_vcol, vcol.name), 
             vcol.name, "") for vcol in mesh.vertex_colors]
        ext = [] if obj.vertex_groups is None else [
            ("{0} {1}".format(type_vgroup, group.name),
             "W: " + group.name, "") for group in obj.vertex_groups]
        items.extend(ext)
        ext = [] if mesh.uv_layers is None else [
            ("{0} {1}".format(type_uv, uv.name),
             "UV: " + uv.name, "") for uv in mesh.uv_layers]
        items.extend(ext)

        return items

    src_vcol_id = EnumProperty(
        name="Source Layer",
        items=vcol_layer_items,
        description="Source (Src) vertex color layer.",
    )

    src_channel_id = EnumProperty(
        name="Source Channel",
        items=channel_items,
        # default=red_id,
        description="Source (Src) color channel."
    )

    dst_vcol_id = EnumProperty(
        name="Destination Layer",
        items=vcol_layer_items,
        description="Destination (Dst) vertex color layer.",
    )

    dst_channel_id = EnumProperty(
        name="Destination Channel",
        items=channel_items,
        # default=green_id,
        description="Destination (Dst) color channel."
    )

    channel_blend_mode = bpy.props.EnumProperty(
        name="Channel Blend Mode",
        items=channel_blend_mode_items,
        description="Channel blending operation.",
    )


class VertexColorMaster(bpy.types.Panel):
    """Add-on for working with vertex color data"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_label = 'Vertex Color Master'
    bl_category =  'Vertex Color Master' # 'Tools'
    bl_context = 'vertexpaint'

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        settings = context.scene.vertex_color_master_settings

        # use active mesh active vcol layer name to determine whether or not
        # we should be in isolate mode or not
        isolate = get_isolated_channel_ids(obj.data.vertex_colors.active)
        if isolate is not None:
            return self.draw_isolate_mode_layout(context, obj, isolate[0], isolate[1], settings)

        self.draw_standard_layout(context, obj, settings)


    def draw_standard_layout(self, context, obj, settings):
        layout = self.layout

        self.draw_brush_settings(context, layout, obj, settings)
        layout.separator()
        self.draw_active_channel_operations(context, layout, obj, settings)
        layout.separator()
        self.draw_src_dst_operations(context, layout, obj, settings)
        layout.separator()
        self.draw_misc_operations(context, layout, obj, settings)


    def draw_isolate_mode_layout(self, context, obj, vcol_id, channel_id, settings):
        layout = self.layout

        col = layout.column()
        row = col.row()
        row.label("Isolated '{0}.{1}'".format(vcol_id, channel_id))

        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator('vertexcolormaster.apply_isolated', "Apply Changes").discard = False
        row = col.row(align=True)
        row.operator('vertexcolormaster.apply_isolated', "Discard Changes").discard = True
        layout.separator()
        self.draw_brush_settings(context, layout, obj, settings, mode='GRAYSCALE')
        layout.separator()
        self.draw_active_channel_operations(context, layout, obj, settings, mode='ISOLATE')
        layout.separator()
        self.draw_misc_operations(context, layout, obj, settings, mode='ISOLATE')


    def draw_brush_settings(self, context, layout, obj, settings, mode='COLOR'):
        brush = bpy.data.brushes['Draw']
        col = layout.column(align=True)
        row = col.row()
        row.label('Brush Settings')

        if mode == 'COLOR':
            row = col.row(align=False)
            row.prop(settings, 'match_brush_to_active_channels')
            row = col.row(align=True)
            row.prop(brush, 'color', text="")
            row.prop(brush, 'secondary_color', text="")
            row.separator()
            row.operator('vertexcolormaster.brush_colors_flip', "", icon='FILE_REFRESH')
            col.separator()
            row = col.row(align=False)
            row.operator('vertexcolormaster.quick_fill', "Fill With Color").fill_color = brush.color
        else:
            row = col.row(align=True)
            row.prop(settings, 'brush_value_isolate', 'Val', slider=True)

        row = layout.row()
        row.prop(brush, 'vertex_tool', text="Blend")
        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator('vertexcolormaster.edit_brush_settings', "Mix").blend_mode = 'MIX'
        row.operator('vertexcolormaster.edit_brush_settings', "Add").blend_mode = 'ADD'
        row.operator('vertexcolormaster.edit_brush_settings', "Sub").blend_mode = 'SUB'
        row.operator('vertexcolormaster.edit_brush_settings', "Blur").blend_mode = 'BLUR'
        row = col.row(align=True)
        row.prop(brush, 'strength', text="Strength")


    def draw_active_channel_operations(self, context, layout, obj, settings, mode='STANDARD'):
        col = layout.column(align=True)

        if mode == 'STANDARD':
            row = col.row()
            row.label('Active Channels')
            row = col.row(align=True)
            row.prop(settings, 'active_channels', expand=True)
            row = col.row(align=True)

            can_isolate = len(settings.active_channels) == 1
            iso_channel_id = 'R'
            if can_isolate:
                for channel_id in settings.active_channels:
                    iso_channel_id = channel_id
                    break

            row.operator('vertexcolormaster.isolate_channel', "Isolate Active Channel").src_channel_id = iso_channel_id
            row.enabled = can_isolate


        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator('vertexcolormaster.fill', 'Fill').value = 1.0
        row.operator('vertexcolormaster.fill', 'Clear').value = 0.0
        row = col.row(align=True)
        row.operator('vertexcolormaster.invert', 'Invert')
        row.operator('vertexcolormaster.posterize', 'Posterize')
        row = col.row(align=True)
        row.operator('vertexcolormaster.remap', 'Remap')


    def draw_src_dst_operations(self, context, layout, obj, settings):
        col = layout.column(align=True)
        row = col.row()
        row.label('Data Transfer')

        layer_info = get_layer_info(context)
        src_type = layer_info[0]
        dst_type = layer_info[2]

        lcol_percentage = 0.8
        row = layout.row()
        split = row.split(lcol_percentage, align=True)
        col = split.column(align=True)
        col.prop(settings, 'src_vcol_id', 'Src')
        split = split.split(align=True)
        col = split.column(align=True)
        col.prop(settings, 'src_channel_id', '')
        col.enabled = src_type == type_vcol and dst_type != type_uv

        row = layout.row()
        split = row.split(lcol_percentage, align=True)
        col = split.column(align=True)
        col.prop(settings, 'dst_vcol_id', 'Dst')
        split = split.split(align=True)
        col = split.column(align=True)
        col.prop(settings, 'dst_channel_id', '')
        col.enabled = dst_type == type_vcol and src_type != type_uv

        if src_type == type_vcol and dst_type == type_vcol:
            row = layout.row(align=True)
            row.operator('vertexcolormaster.copy_channel', 'Copy').swap_channels = False
            row.operator('vertexcolormaster.copy_channel', 'Swap').swap_channels = True

            col = layout.column(align=True)
            row = col.row()
            row.operator('vertexcolormaster.blend_channels', 'Blend').blend_mode = settings.channel_blend_mode
            row.prop(settings, 'channel_blend_mode', '')

            col = layout.column(align=True)
            row = col.row(align=True)
            row.operator('vertexcolormaster.rgb_to_grayscale',
                         'Src RGB to luminosity')
            row = col.row(align=True)
            row.operator('vertexcolormaster.copy_channel', 'Src ({0}) to Dst RGB'.format(
                settings.src_channel_id)).all_channels = True
        elif src_type == type_vgroup and dst_type == type_vcol:
            row = layout.row(align=True)
            row.operator('vertexcolormaster.weights_to_color',
                         'Weights to Dst ({0})'.format(settings.dst_channel_id))
        elif src_type == type_vcol and dst_type == type_vgroup:
            row = layout.row(align=True)
            row.operator('vertexcolormaster.color_to_weights',
                         'Src ({0}) to Weights'.format(settings.src_channel_id))
        elif src_type == type_uv and dst_type == type_vcol:
            row = layout.row(align=True)
            row.operator('vertexcolormaster.uvs_to_color',
                         'UVs to Dst')
        elif src_type == type_vcol and dst_type == type_uv:
            row = layout.row(align=True)
            row.operator('vertexcolormaster.color_to_uvs', 'Src to UVs')
        else:
            # unsupported: vgroup <-> vgroup, uv <-> uv, vgroup <-> uv
            row = layout.row(align=True)
            row.label("Src > Dst is unsupported")

    def draw_misc_operations(self, context, layout, obj, settings, mode='STANDARD'):
        col = layout.column(align=True)
        row = col.row()
        row.label('Misc Operations')

        col = layout.column(align=True)
        if mode == 'STANDARD':
            row = col.row(align=True)
            row.operator('vertexcolormaster.randomise_mesh_island_colors', "Randomise Mesh Island Colors")
            row = col.row(align=True)
            row.operator('vertexcolormaster.adjust_hsv', "Adjust HSV")
        row = col.row(align=True)
        row.operator('vertexcolormaster.linear_gradient', "Gradient Tool")
        

###############################################################################
# OPERATOR REGISTRATION
###############################################################################

def register():
    bpy.utils.register_class(VertexColorMasterProperties)
    bpy.types.Scene.vertex_color_master_settings = PointerProperty(
        type=VertexColorMasterProperties)

    bpy.utils.register_class(VertexColorMaster)
    bpy.utils.register_class(VertexColorMaster_QuickFill)
    bpy.utils.register_class(VertexColorMaster_Fill)
    bpy.utils.register_class(VertexColorMaster_Invert)
    bpy.utils.register_class(VertexColorMaster_Posterize)
    bpy.utils.register_class(VertexColorMaster_Remap)
    bpy.utils.register_class(VertexColorMaster_CopyChannel)
    bpy.utils.register_class(VertexColorMaster_RgbToGrayscale)
    bpy.utils.register_class(VertexColorMaster_BlendChannels)
    bpy.utils.register_class(VertexColorMaster_EditBrushSettings)
    bpy.utils.register_class(VertexColorMaster_WeightsToColor)
    bpy.utils.register_class(VertexColorMaster_ColorToWeights)
    bpy.utils.register_class(VertexColorMaster_UVsToColor)
    bpy.utils.register_class(VertexColorMaster_ColorToUVs)
    bpy.utils.register_class(VertexColorMaster_IsolateChannel)
    bpy.utils.register_class(VertexColorMaster_ApplyIsolatedChannel)
    bpy.utils.register_class(VertexColorMaster_RandomiseMeshIslandColors)
    bpy.utils.register_class(VertexColorMaster_LinearGradient)
    bpy.utils.register_class(VertexColorMaster_AdjustHSV)
    bpy.utils.register_class(VertexColorMaster_FlipBrushColors)

def unregister():
    bpy.utils.unregister_class(VertexColorMasterProperties)
    del bpy.types.Scene.vertex_color_master_settings

    bpy.utils.unregister_class(VertexColorMaster)
    bpy.utils.unregister_class(VertexColorMaster_QuickFill)
    bpy.utils.unregister_class(VertexColorMaster_Fill)
    bpy.utils.unregister_class(VertexColorMaster_Invert)
    bpy.utils.unregister_class(VertexColorMaster_Posterize)
    bpy.utils.unregister_class(VertexColorMaster_Remap)
    bpy.utils.unregister_class(VertexColorMaster_CopyChannel)
    bpy.utils.unregister_class(VertexColorMaster_RgbToGrayscale)
    bpy.utils.unregister_class(VertexColorMaster_BlendChannels)
    bpy.utils.unregister_class(VertexColorMaster_EditBrushSettings)
    bpy.utils.unregister_class(VertexColorMaster_WeightsToColor)
    bpy.utils.unregister_class(VertexColorMaster_ColorToWeights)
    bpy.utils.unregister_class(VertexColorMaster_UVsToColor)
    bpy.utils.unregister_class(VertexColorMaster_ColorToUVs)
    bpy.utils.unregister_class(VertexColorMaster_IsolateChannel)
    bpy.utils.unregister_class(VertexColorMaster_ApplyIsolatedChannel)
    bpy.utils.unregister_class(VertexColorMaster_RandomiseMeshIslandColors)
    bpy.utils.unregister_class(VertexColorMaster_LinearGradient)
    bpy.utils.unregister_class(VertexColorMaster_AdjustHSV)
    bpy.utils.unregister_class(VertexColorMaster_FlipBrushColors)


# allows running addon from text editor
if __name__ == '__main__':
    register()
