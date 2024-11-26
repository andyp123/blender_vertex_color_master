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

import bpy
from bpy.types import Menu
from bpy.props import *

from .vcm_globals import *
from .vcm_helpers import (
    get_isolated_channel_ids,
    get_layer_info,
)


class VERTEXCOLORMASTER_PT_MainPanel(bpy.types.Panel):
    """Add-on for working with vertex color data"""
    bl_label = 'Vertex Color Master'
    bl_idname = 'VERTEXCOLORMASTER_PT_MainPanel'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category =  'VCM'
    bl_context = 'vertexpaint'
    # bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        settings = context.scene.vertex_color_master_settings

        if not obj.data.vertex_colors.active:
            layout.label(text="No active vertex color layer")
            return

        # use active mesh active vcol layer name to determine whether or not
        # should we be in isolate mode or not
        isolate = get_isolated_channel_ids(obj.data.vertex_colors.active)
        if isolate is not None:
            return self.draw_isolate_mode_layout(context, obj, isolate[0], isolate[1], settings)

        self.draw_standard_layout(context, obj, settings)


    def draw_standard_layout(self, context, obj, settings):
        layout = self.layout

        draw_brush_settings(context, layout, obj, settings)
        layout.separator()
        draw_active_channel_operations(context, layout, obj, settings)
        layout.separator()
        draw_src_dst_operations(context, layout, obj, settings)
        layout.separator()
        draw_misc_operations(context, layout, obj, settings)


    def draw_isolate_mode_layout(self, context, obj, vcol_id, channel_id, settings):
        layout = self.layout

        col = layout.column()
        row = col.row()
        row.label(text="Isolated '{0}.{1}'".format(vcol_id, channel_id))

        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator('vertexcolormaster.apply_isolated', text="Apply Changes").discard = False
        row = col.row(align=True)
        row.operator('vertexcolormaster.apply_isolated', text="Discard Changes").discard = True
        layout.separator()
        draw_brush_settings(context, layout, obj, settings, mode='ISOLATE')
        layout.separator()
        draw_active_channel_operations(context, layout, obj, settings, mode='ISOLATE')
        layout.separator()
        draw_misc_operations(context, layout, obj, settings, mode='ISOLATE')


class VERTEXCOLORMASTER_MT_PieMain(Menu):
    # label is displayed at the center of the pie menu.
    bl_label = "Vertex Color Master"
    bl_idname = "VERTEXCOLORMASTER_MT_PieMain"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        # FIXME: this is not working for some reason...
        return obj is not None # and obj.mode is 'VERTEX_PAINT'

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        settings = context.scene.vertex_color_master_settings
        isolate = get_isolated_channel_ids(obj.data.vertex_colors.active)
        mode = 'STANDARD' if isolate is None else 'ISOLATE'

        # create top level pie layout
        pie = layout.menu_pie()

        # need container layouts for each pie direction (L,R,B,T,TL,TR,BL,BR order)
        col = pie.column() # Left
        draw_brush_settings(context, col, obj, settings, mode, pie=True)
        # col.separator()
        col = pie.column() # Right
        draw_active_channel_operations(context, col, obj, settings, mode, pie=True)
        col.separator()
        draw_misc_operations(context, col, obj, settings, mode, pie=True)
        col = pie.column() # Bottom
        col = pie.column() # Top
        if isolate is None:
            row = col.row()
            # row.alignment = 'CENTER'
            row.emboss = 'RADIAL_MENU'
            row.label(text="Isolate Channel")
            row = col.row()
            row.operator('vertexcolormaster.isolate_channel', text="R").src_channel_id = red_id
            row.operator('vertexcolormaster.isolate_channel', text="G").src_channel_id = green_id
            row.operator('vertexcolormaster.isolate_channel', text="B").src_channel_id = blue_id
            row.operator('vertexcolormaster.isolate_channel', text="A").src_channel_id = alpha_id
        else:
            row = col.row()
            row.emboss = 'RADIAL_MENU'
            row.label(text="Isolated '{0}.{1}'".format(isolate[0], isolate[1]))            
            row = col.row(align=True)
            row.operator('vertexcolormaster.apply_isolated', text="Apply Changes").discard = False
            row.operator('vertexcolormaster.apply_isolated', text="Discard Changes").discard = True


# Menu functions for drawing sub-panels
def draw_brush_settings(context, layout, obj, settings, mode='STANDARD', pie=False):
    brush = context.tool_settings.vertex_paint.brush
    col = layout.column()
    row = col.row()
    if pie:
        row.emboss = 'RADIAL_MENU'
    row.label(text="Brush Settings")

    if mode == 'STANDARD' and not pie:
        row = col.row(align=False)
        row.prop(settings, 'use_grayscale')
        row = col.row(align=False)
        row.prop(settings, 'match_brush_to_active_channels')

    if mode != 'STANDARD' or settings.use_grayscale:
        row = col.row(align=True)
        row.prop(settings, 'brush_value_isolate', text="F", slider=True)
        row.prop(settings, 'brush_secondary_value_isolate', text="B", slider=True)
        row.separator()
        row.operator('vertexcolormaster.brush_colors_flip', text="", icon='FILE_REFRESH')
        row = col.row(align=False)
        row.operator('paint.vertex_color_set', text="Fill With Value")
    else:
        row = col.row(align=True)
        row.prop(brush, 'color', text="")
        row.prop(brush, 'secondary_color', text="")
        row.separator()
        row.operator('vertexcolormaster.brush_colors_flip', text="", icon='FILE_REFRESH')
        row = col.row(align=False)
        row.operator('paint.vertex_color_set', text="Fill With Color")

    col = layout.column(align=True)
    row = col.row(align=True)
    row.operator('vertexcolormaster.edit_brush_settings', text="Mix").blend_mode = 'MIX'
    row.operator('vertexcolormaster.edit_brush_settings', text="Add").blend_mode = 'ADD'
    row.operator('vertexcolormaster.edit_brush_settings', text="Sub").blend_mode = 'SUB'
    row.operator('vertexcolormaster.edit_brush_settings', text="Blur").blend_mode = 'BLUR'
    row = col.row(align=True)
    row.prop(brush, 'strength', text="Strength")
    if mode == 'STANDARD':
        row = col.row(align=True)
        row.prop(brush, 'use_alpha', text="Affect Alpha")


def draw_active_channel_operations(context, layout, obj, settings, mode='STANDARD', pie=False):
    if pie:
        if mode == 'STANDARD':
            return None
        row = layout.row()
        row.emboss = 'RADIAL_MENU'
        row.label(text="Basic Operations")

    if mode == 'STANDARD':
        col = layout.column(align=True)
        row = col.row()
        row.label(text="Active Channels")
        row = col.row(align=True)
        row.prop(settings, 'active_channels', expand=True)
        row = col.row(align=True)

        can_isolate = len(settings.active_channels) == 1
        iso_channel_id = 'R'
        if can_isolate:
            for channel_id in settings.active_channels:
                iso_channel_id = channel_id
                break

        row.operator('vertexcolormaster.isolate_channel',
            text="Isolate Active Channel").src_channel_id = iso_channel_id
        row.enabled = can_isolate

    col = layout.column(align=True)

    row = col.row(align=True)
    row.operator('vertexcolormaster.fill', text='Fill').value = 1.0
    row.operator('vertexcolormaster.fill', text='Clear').value = 0.0
    row = col.row(align=True)
    if mode == 'STANDARD':
        row.operator('vertexcolormaster.invert', text='Invert')
    else:
        # Use built-in, as it's much faster
        row.operator('paint.vertex_color_invert', text='Invert')
    row.operator('vertexcolormaster.posterize', text='Posterize')
    row = col.row(align=True)
    row.operator('vertexcolormaster.remap', text='Remap')
    if mode == 'STANDARD':
        row.operator('vertexcolormaster.randomize_mesh_island_colors_per_channel', text='Islands')


def draw_src_dst_operations(context, layout, obj, settings):
    col = layout.column(align=True)
    row = col.row()
    row.label(text="Data Transfer")

    layer_info = get_layer_info(context)
    src_type = layer_info[0]
    dst_type = layer_info[2]

    lcol_percentage = 0.8
    row = layout.row()
    split = row.split(factor=lcol_percentage, align=True)
    col = split.column(align=True)
    col.prop(settings, 'src_vcol_id', text="Src")
    split = split.split(align=True)
    col = split.column(align=True)
    col.prop(settings, 'src_channel_id', text="")
    col.enabled = src_type == type_vcol and (dst_type == type_vcol or dst_type == type_vgroup)

    row = layout.row()
    split = row.split(factor=lcol_percentage, align=True)
    col = split.column(align=True)
    col.prop(settings, 'dst_vcol_id', text="Dst")
    split = split.split(align=True)
    col = split.column(align=True)
    col.prop(settings, 'dst_channel_id', text="")
    col.enabled = dst_type == type_vcol and (src_type == type_vcol or src_type == type_vgroup)

    if src_type == type_vcol and dst_type == type_vcol:
        row = layout.row(align=True)
        row.operator('vertexcolormaster.copy_channel', text="Copy").swap_channels = False
        op = row.operator('vertexcolormaster.copy_channel', text="Swap")
        op.swap_channels = True
        op.all_channels = False

        col = layout.column(align=True)
        row = col.row()
        row.operator('vertexcolormaster.blend_channels', text="Blend").blend_mode = settings.channel_blend_mode
        row.prop(settings, 'channel_blend_mode', text="")

        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator('vertexcolormaster.rgb_to_grayscale',
            text="Src RGB to luminosity")
        row = col.row(align=True)
        row.operator('vertexcolormaster.copy_channel', text="Src ({0}) to Dst RGB".format(
            settings.src_channel_id)).all_channels = True
    elif src_type == type_vgroup and dst_type == type_vcol:
        row = layout.row(align=True)
        row.operator('vertexcolormaster.weights_to_color',
            text="Weights to Dst ({0})".format(settings.dst_channel_id))
    elif src_type == type_vcol and dst_type == type_vgroup:
        row = layout.row(align=True)
        row.operator('vertexcolormaster.color_to_weights',
            text="Src ({0}) to Weights".format(settings.src_channel_id))
    elif src_type == type_uv and dst_type == type_vcol:
        row = layout.row(align=True)
        row.operator('vertexcolormaster.uvs_to_color', text="UVs to Color")
    elif src_type == type_vcol and dst_type == type_uv:
        row = layout.row(align=True)
        row.operator('vertexcolormaster.color_to_uvs', text="Color to UVs")
    elif src_type == type_normal and dst_type == type_vcol:
        row = layout.row(align=True)
        row.operator('vertexcolormaster.normals_to_color', text="Normals to Color")
    elif src_type == type_vcol and dst_type == type_normal:
        row = layout.row(align=True)
        row.operator('vertexcolormaster.color_to_normals', text="Color to Normals")
    else:
        # unsupported: vgroup <-> vgroup, uv <-> uv, vgroup <-> uv
        row = layout.row(align=True)
        row.label(text="Src > Dst is unsupported")


def draw_misc_operations(context, layout, obj, settings, mode='STANDARD', pie=False):
    col = layout.column(align=True)
    row = col.row()
    if pie:
        row.emboss = 'RADIAL_MENU'
    row.label(text="Misc Operations")

    col = layout.column(align=True)
    if mode == 'STANDARD':
        row = col.row(align=True)
        row.operator('paint.vertex_color_hsv', text="Adjust HSV")
    else:
        row = col.row(align=True)
        row.operator('vertexcolormaster.blur_channel', text="Blur Channel Values")
    row = col.row(align=True)
    row.operator('vertexcolormaster.randomize_mesh_island_colors', text="Random Mesh Island Colors")
    row = col.row(align=True)
    row.operator('paint.vertex_color_brightness_contrast', text="Brightness/Contrast")
    row = col.row(align=True)
    row.operator('paint.vertex_color_dirt', text="Dirty Vertex Colors")

    col = layout.column(align=True)
    row = col.row(align=True)
    row.operator('vertexcolormaster.gradient', text="Linear Gradient").circular_gradient = False
    row = col.row(align=True)
    row.operator('vertexcolormaster.gradient', text="Circular Gradient").circular_gradient = True
