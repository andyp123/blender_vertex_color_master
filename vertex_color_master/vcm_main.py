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
from mathutils import Color
from .vcm_globals import *
from .vcm_helpers import rgb_to_luminosity

# VERTEXCOLORMASTER_Properties
class VertexColorMasterProperties(bpy.types.PropertyGroup):

    def update_active_channels(self, context):
        if self.use_grayscale or not self.match_brush_to_active_channels:
            return None

        active_channels = self.active_channels

        # set draw color based on mask
        draw_color = [0.0, 0.0, 0.0]
        if red_id in active_channels:
            draw_color[0] = 1.0
        if green_id in active_channels:
            draw_color[1] = 1.0
        if blue_id in active_channels:
            draw_color[2] = 1.0

        context.tool_settings.vertex_paint.brush.color = draw_color

        return None

    def update_brush_value_isolate(self, context):
        brush = context.tool_settings.vertex_paint.brush
        v1 = self.brush_value_isolate
        v2 = self.brush_secondary_value_isolate
        brush.color = Color((v1, v1, v1))
        brush.secondary_color = Color((v2, v2, v2))

        return None

    def toggle_grayscale(self, context):
        brush = context.tool_settings.vertex_paint.brush

        if self.use_grayscale:
            self.brush_color = brush.color
            self.brush_secondary_color = brush.secondary_color

            v1 = self.brush_value_isolate
            v2 = self.brush_secondary_value_isolate
            brush.color = Color((v1, v1, v1))
            brush.secondary_color = Color((v2, v2, v2))
        else:
            brush.color = self.brush_color
            brush.secondary_color = self.brush_secondary_color

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

    use_grayscale: BoolProperty(
        name="Use Grayscale",
        default=False,
        description="Show grayscale values instead of RGB colors.",
        update=toggle_grayscale
    )

    # Used only to store the color between RGBA and isolate modes
    brush_color: FloatVectorProperty(
        name="Brush Color",
        description="Brush primary color.",
        default=(1, 0, 0)
    )

    brush_secondary_color: FloatVectorProperty(
        name="Brush Secondary Color",
        description="Brush secondary color.",
        default=(1, 0, 0)
    )

    # Replacement for color in the isolate mode UI
    brush_value_isolate: FloatProperty(
        name="Brush Value",
        description="Value of the brush color.",
        default=1.0,
        min=0.0, max=1.0,
        update=update_brush_value_isolate
    )

    brush_secondary_value_isolate: FloatProperty(
        name="Brush Value",
        description="Value of the brush secondary color.",
        default=0.0,
        min=0.0, max=1.0,
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
        ext = [("{0} {1}".format(type_normal, "Normals"), "Normals", "")]
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
   