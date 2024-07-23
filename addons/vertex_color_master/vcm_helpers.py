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

# <pep8 compliant>


# COMMON IDENTIFIERS:

# PARAMETERS
# src_attr, dst_attr : source and destination Attributes (containing array of per vertex or corner data)
# src_channel_idx, dst_channel_idx : source and destination channel indices (0-3)

# LOCAL VARIABLES
# src_av, dst_av : source and destination Attribute Values (e.g. src_attr.data[i].color)
# src_cv, dst_cv : source and destination channel values (e.g. src_attr.data[i].color[src_channel_idx])


import bpy
import bmesh
import random
from math import fmod
from mathutils import Color, Vector
from .vcm_globals import *


def posterize(value, steps):
    return round(value * steps) / steps


def remap(value, min0, max0, min1, max1):
    r0 = max0 - min0
    if r0 == 0:
        return min1
    r1 = max1 - min1
    return ((value - min0) * r1) / r0 + min1


def channel_id_to_idx(id):
    if id == red_id:
        return 0
    if id == green_id:
        return 1
    if id == blue_id:
        return 2
    if id == alpha_id:
        return 3
    # default to red
    return 0


def get_active_channel_mask(active_channels):
    rgba_mask = [True if cid in active_channels else False for cid in valid_channel_ids]
    return rgba_mask


def get_isolated_channel_ids(vcol):
    if vcol is not None:
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


# Blender now uses Attributes for everything. vcol channels are attributes, and colors are vectors
# Must check domain and type are the same between src + destination or conversion is required

# TODO: Should this copy channels of ANY kind of attribute?
# ByteColorAttribute (RGBA 8bit), FloatColorAttribute (RGBA 32bit) < For colours

# Other Attribute types:
# BoolAttribute, ByteColorAttribute, ByteIntAttribute, Float2Attribute, Float4x4Attribute, FloatAttribute,
# FloatVectorAttribute, Int2Attribute, IntAttribute, QuaternionAttribute, StringAttribute

# src_attribute: Source attribute (ByteColorAttribute or FloatColorAttribute)
# dst_attribute: Destination attribute (Attribute of same data_type and domain as src_attr)
# src_channel_idx: Source channel (0-3)
# dst_channel_idx: Destination channel (0-3)

# alpha_mode: When copying to all channels, what to do with the alpha channel
# 'USE_SRC' - keep existing alpha value from source
# 'USE_DST' - keep existing alpha value from destination
# 'FILL' - fill alpha with 1.0
def copy_channel(mesh, src_attribute, dst_attribute, src_channel_idx, dst_channel_idx,
                 swap=False, dst_all_channels=False, alpha_mode='USE_SRC'):
    if src_attribute.data_type != dst_attribute.data_type or src_attribute.domain != dst_attribute.domain:
        return

    if dst_all_channels: # typically used by isolate mode
        if alpha_mode == 'FILL':
            for i, src_av in enumerate(src_attribute.data):
                src_cv = src_av.color[src_channel_idx]
                dst_attribute.data[i].color = [src_cv, src_cv, src_cv, 1.0]
        elif alpha_mode == 'USE_DST':
            for i, src_av in enumerate(src_attribute.data):
                src_cv = src_av.color[src_channel_idx]
                dst_alpha = dst_attribute.data[i].color[3]
                dst_attribute.data[i].color = [src_cv, src_cv, src_cv, dst_alpha]
        else: # 'KEEP_SRC'
            for i, src_av in enumerate(src_attribute.data):
                src_cv = src_av.color[src_channel_idx]
                dst_attribute.data[i].color = [src_cv, src_cv, src_cv, src_av.color[3]]
    else:
        if swap:
            for i in range(len(src_attribute.data)):
                src_cv = src_attribute.data[i].color[src_channel_idx]
                dst_cv = dst_attribute.data[i].color[dst_channel_idx]
                src_attribute.data[i].color[src_channel_idx] = dst_cv
                dst_attribute.data[i].color[dst_channel_idx] = src_cv
        else:
            for i, src_av in enumerate(src_attribute.data):
                dst_attribute.data[i].color[dst_channel_idx] = src_av.color[src_channel_idx]

    mesh.update()


# TODO: Should this also use a result attribute?
def blend_channels(mesh, src_attribute, dst_attribute, src_channel_idx, dst_channel_idx,
                   result_channel_idx, operation='ADD'):
    if operation == 'ADD':
        for i, src_av in enumerate(src_attr.data):
            val = src_av.color[src_channel_idx] + dst_attribute.data[i].color[dst_channel_idx]
            dst_attribute.data[i].color[result_channel_idx] = max(0.0, min(val, 1.0)) # clamp
    elif operation == 'SUB':
        for i, src_av in enumerate(src_attr.data):
            val = src_av.color[src_channel_idx] - dst_attribute.data[i].color[dst_channel_idx]
            dst_attribute.data[i].color[result_channel_idx] = max(0.0, min(val, 1.0)) # clamp
    elif operation == 'MUL':
        for i, src_av in enumerate(src_attr.data):
            val = src_av.color[src_channel_idx] * dst_attribute.data[i].color[dst_channel_idx]
            dst_attribute.data[i].color[result_channel_idx] = val
    elif operation == 'DIV':
        for i in range(len(src_attr.data)):
            src_cv = src_attribute.data[i].color[src_channel_idx]
            dst_cv = dst_attribute.data[i].color[dst_channel_idx]
            val = 1.0 if dst_cv == 0.0 else src_cv / dst_cv
            dst_attribute.data[i].color[result_channel_idx] = max(0.0, min(val, 1.0)) # clamp
    elif operation == 'LIGHTEN':
        for i in range(len(src_attr.data)):
            src_cv = src_attribute.data[i].color[src_channel_idx]
            dst_cv = dst_attribute.data[i].color[dst_channel_idx]
            dst_attribute.data[i].color[result_channel_idx] = src_cv if src_cv > dst_cv else dst_cv
    elif operation == 'DARKEN':
        for i in range(len(src_attr.data)):
            src_cv = src_attribute.data[i].color[src_channel_idx]
            dst_cv = dst_attribute.data[i].color[dst_channel_idx]
            dst_attribute.data[i].color[result_channel_idx] = src_cv if src_cv < dst_cv else dst_cv
    elif operation == 'MIX':
        for i, src_av in enumerate(src_attr.data):
            dst_attribute.data[i].color[result_channel_idx] = src_av.color[src_channel_idx]
    else: # UNDEFINED
        return

    mesh.update()


# TODO: Properly deal with UV and normal attributes later
def uvs_to_color(mesh, src_uv, dst_vcol, dst_u_idx=0, dst_v_idx=1):
    # by default copy u->r and v->g
    # uv range is -inf, inf so use fmod to remap to 0-1
    for loop_index, loop in enumerate(mesh.loops):
        c = dst_vcol.data[loop_index].color
        uv = src_uv.data[loop_index].uv
        u = fmod(uv[0], 1.0)
        v = fmod(uv[1], 1.0)
        c[dst_u_idx] = u + 1.0 if u < 0 else u
        c[dst_v_idx] = v + 1.0 if v < 0 else v
        dst_vcol.data[loop_index].color = c

    mesh.update()


# TODO: Does this make any sense? Data loss is likely to occur,
# and it's too niche to do properly (create uv islands based on contiguousness)
def color_to_uvs(mesh, src_vcol, dst_uv, src_u_idx=0, src_v_idx=1):
    # by default copy r->u and g->v
    for loop_index, loop in enumerate(mesh.loops):
        c = src_vcol.data[loop_index].color
        uv = [c[src_u_idx], c[src_v_idx]]
        dst_uv.data[loop_index].uv = uv

    mesh.update()


def get_custom_normals(obj):
    # Not entirely sure why this works and [loop.normal for loop in obj.data.loops] doesn't work...
    # note that these normals are in world space... seems to be a huge pain to get tangent space normals
    normals = [loop.normal for loop in [obj.data.calc_normals_split(), obj][1].data.loops]

    return normals


def normals_to_color(mesh, normals, dst_vcol):
    # copy normal xyz to color rgb
    for loop_index, loop in enumerate(mesh.loops):
        c = dst_vcol.data[loop_index].color
        n = normals[loop_index]
        # remap to values that can be displayed
        c[0] = remap(n[0], -1.0, 1.0, 0.0, 1.0)
        c[1] = remap(n[1], -1.0, 1.0, 0.0, 1.0)
        c[2] = remap(n[2], -1.0, 1.0, 0.0, 1.0)
        dst_vcol.data[loop_index].color = c

    mesh.update()


# TODO: Remove this, as it's likely not useful
def color_to_normals(mesh, src_vcol):
    # ensure the mesh has empty split normals
    if not mesh.has_custom_normals:
        mesh.create_normals_split()
        mesh.use_auto_smooth = True

    # create a structure that matches the required input of the normals_split_custom_set function
    clnors = [Vector()] * len(mesh.loops)

    for loop_index, loop in enumerate(mesh.loops):
        c = src_vcol.data[loop_index].color
        # remap color to normal range
        n = Vector([remap(channel, 0.0, 1.0, -1.0, 1.0) for channel in c[0:3]])
        n.normalize()
        clnors[loop_index] = n   

    mesh.normals_split_custom_set(clnors)   
    mesh.update()  


def weights_to_color(mesh, src_vgroup_idx, dst_vcol, dst_channel_idx, all_channels=False):
    vertex_weights = [0.0] * len(mesh.vertices)

    # build list of weights for vertex indices
    for i, vert in enumerate(mesh.vertices):
        for group in vert.groups:
            if group.group == src_vgroup_idx:
                vertex_weights[i] = group.weight
                break

    # copy weights to channel of dst color layer
    if not all_channels:
        for loop_index, loop in enumerate(mesh.loops):
            weight = vertex_weights[loop.vertex_index]
            dst_vcol.data[loop_index].color[dst_channel_idx] = weight
    else:
        for loop_index, loop in enumerate(mesh.loops):
            weight = vertex_weights[loop.vertex_index]
            dst_vcol.data[loop_index].color[:3] = [weight]*3

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


# check isolate mode (shouldn't work in isolate mode...)
# set random seed in parent function
def set_island_colors_per_channel(mesh, rgba_mask, merge_similar, vmin, vmax):
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

    for index, island in enumerate(mesh_islands):
        rgba_values = []

        face_count = len(island)
        if merge_similar and face_count in island_colors.keys():
            rgba_values = island_colors[face_count]
        else:
            vrange = abs(vmax - vmin)
            rgba_values = [(vmin + random.random() * vrange) for i in range(4)]
            island_colors[face_count] = rgba_values

        # Set island face colors (probably quite slow, due to list comprehension per face loop)
        for face in island:
            for loop in face.loops:
                c = loop[color_layer]
                c = [v if rgba_mask[i] else c[i] for i, v in enumerate(rgba_values)]
                loop[color_layer] = c

    # Restore selection
    for f in selected_faces:
        f.select = True

    bm.free()
    bpy.ops.object.mode_set(mode='VERTEX_PAINT', toggle=False)


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


# TODO: This needs rewriting due to change from vertex_colors to color_attributes
# It must support POINT or CORNER with BYTE_COLOR or FLOAT_COLOR combinations
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
        if (src_type == type_vcol or dst_type == type_vcol) and mesh.color_attributes is None:
            message = "Object has no vertex colors."
        if (src_type == type_vgroup or dst_type == type_vgroup) and obj.vertex_groups is None:
            message = "Object has no vertex groups."
        if (src_type == type_uv or dst_type == type_uv) and mesh.uv_layers is None:
            message = "Object has no uv layers."

    # validate src
    if get_src and message is None:
        if src_type == type_vcol:
            if src_id in mesh.color_attributes:
                rv['src_vcol'] = mesh.color_attributes[src_id]
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
            if dst_id in mesh.color_attributes:
                rv['dst_vcol'] = mesh.color_attributes[dst_id]
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
