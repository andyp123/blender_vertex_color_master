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
from bpy.props import *
from .vcm_globals import *
from .vcm_helpers import (
    get_isolated_channel_ids,
    get_layer_info,
)

# VERTEXCOLORMASTER_Properties
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

    active_channels: EnumProperty(
        name="Active Channels",
        options={'ENUM_FLAG'},
        items=channel_items,
        description="Which channels to enable.",
        default={'R', 'G', 'B'},
        update=update_active_channels
    )

    match_brush_to_active_channels: BoolProperty(
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
    brush_color: FloatVectorProperty(
        name="Brush Color",
        description="Color of the brush.",
        default=(1, 0, 0)
    )

    brush_value: FloatProperty(
        name="Brush Value",
        description="Value of the brush color.",
        default=1.0,
        min=0.0,
        max=1.0,
        update=update_brush_value
    )

    brush_value_isolate: FloatProperty(
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

    src_vcol_id: EnumProperty(
        name="Source Layer",
        items=vcol_layer_items,
        description="Source (Src) vertex color layer.",
    )

    src_channel_id: EnumProperty(
        name="Source Channel",
        items=channel_items,
        # default=red_id,
        description="Source (Src) color channel."
    )

    dst_vcol_id: EnumProperty(
        name="Destination Layer",
        items=vcol_layer_items,
        description="Destination (Dst) vertex color layer.",
    )

    dst_channel_id: EnumProperty(
        name="Destination Channel",
        items=channel_items,
        # default=green_id,
        description="Destination (Dst) color channel."
    )

    channel_blend_mode: bpy.props.EnumProperty(
        name="Channel Blend Mode",
        items=channel_blend_mode_items,
        description="Channel blending operation.",
    )


class VERTEXCOLORMASTER_PT_MainPanel(bpy.types.Panel):
    """Add-on for working with vertex color data"""
    bl_label = 'Vertex Color Master'
    bl_idname = 'VERTEXCOLORMASTER_PT_MainPanel'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category =  'View'
    bl_context = 'vertexpaint'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        settings = context.scene.vertex_color_master_settings

        # use active mesh active vcol layer name to determine whether or not
        # should we be in isolate mode or not
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
        row.label(text="Isolated '{0}.{1}'".format(vcol_id, channel_id))

        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator('vertexcolormaster.apply_isolated', text="Apply Changes").discard = False
        row = col.row(align=True)
        row.operator('vertexcolormaster.apply_isolated', text="Discard Changes").discard = True
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
        row.label(text="Brush Settings")

        if mode == 'COLOR':
            row = col.row(align=False)
            row.prop(settings, 'match_brush_to_active_channels')
            row = col.row(align=True)
            row.prop(brush, 'color', text="")
            row.prop(brush, 'secondary_color', text="")
            row.separator()
            row.operator('vertexcolormaster.brush_colors_flip', text="", icon='FILE_REFRESH')
            col.separator()
            row = col.row(align=False)
            row.operator('vertexcolormaster.quick_fill', text="Fill With Color").fill_color = brush.color
        else:
            row = col.row(align=True)
            row.prop(settings, 'brush_value_isolate', text="Val", slider=True)

        row = layout.row()
        row.prop(brush, 'blend', text="Blend")
        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator('vertexcolormaster.edit_brush_settings', text="Mix").blend_mode = 'MIX'
        row.operator('vertexcolormaster.edit_brush_settings', text="Add").blend_mode = 'ADD'
        row.operator('vertexcolormaster.edit_brush_settings', text="Sub").blend_mode = 'SUB'
        row.operator('vertexcolormaster.edit_brush_settings', text="Blur").blend_mode = 'BLUR'
        row = col.row(align=True)
        row.prop(brush, 'strength', text="Strength")


    def draw_active_channel_operations(self, context, layout, obj, settings, mode='STANDARD'):
        col = layout.column(align=True)

        if mode == 'STANDARD':
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
        row.operator('vertexcolormaster.invert', text='Invert')
        row.operator('vertexcolormaster.posterize', text='Posterize')
        row = col.row(align=True)
        row.operator('vertexcolormaster.remap', text='Remap')


    def draw_src_dst_operations(self, context, layout, obj, settings):
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
        col.enabled = src_type == type_vcol and dst_type != type_uv

        row = layout.row()
        split = row.split(factor=lcol_percentage, align=True)
        col = split.column(align=True)
        col.prop(settings, 'dst_vcol_id', text="Dst")
        split = split.split(align=True)
        col = split.column(align=True)
        col.prop(settings, 'dst_channel_id', text="")
        col.enabled = dst_type == type_vcol and src_type != type_uv

        if src_type == type_vcol and dst_type == type_vcol:
            row = layout.row(align=True)
            row.operator('vertexcolormaster.copy_channel', text="Copy").swap_channels = False
            row.operator('vertexcolormaster.copy_channel', text="Swap").swap_channels = True

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
            row.operator('vertexcolormaster.uvs_to_color', text="UVs to Dst")
        elif src_type == type_vcol and dst_type == type_uv:
            row = layout.row(align=True)
            row.operator('vertexcolormaster.color_to_uvs', text="Src to UVs")
        else:
            # unsupported: vgroup <-> vgroup, uv <-> uv, vgroup <-> uv
            row = layout.row(align=True)
            row.label(text="Src > Dst is unsupported")

    def draw_misc_operations(self, context, layout, obj, settings, mode='STANDARD'):
        col = layout.column(align=True)
        row = col.row()
        row.label(text="Misc Operations")

        col = layout.column(align=True)
        if mode == 'STANDARD':
            row = col.row(align=True)
            row.operator('vertexcolormaster.randomize_mesh_island_colors', text="Randomize Mesh Island Colors")
            row = col.row(align=True)
            row.operator('vertexcolormaster.adjust_hsv', text="Adjust HSV")
        row = col.row(align=True)
        row.operator('vertexcolormaster.gradient', "Gradient Tool")
        