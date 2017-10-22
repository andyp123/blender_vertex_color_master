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
# + Operate on selection only (VERT/EDGE, FACE)
# + Quick channel preview / view as greyscale / isolate
# + Scale/change range of channel values
# + Add more operator options to REDO panel
# + Improve alpha support:
#  - Auto detect instead of enabled in prefs
#  - Enable RGB channels by default

import bpy
from bpy.props import *
from mathutils import Color

bl_info = {
    "name": "Vertex Color Master",
    "author": "Andrew Palmer",
    "version": (0, 0, 1),
    "blender": (2, 79, 0),
    "location": "View3D > Tools > Vertex Color Master",
    "description": "Tools for manipulating vertex color data.",
    "category": "Paint"
}

red_id = 'R'
green_id = 'G'
blue_id = 'B'
alpha_id = 'A'


def channel_items(self, context):
    prefs = context.user_preferences.addons[__name__].preferences
    items = [(red_id, "R", ""), (green_id, "G", ""), (blue_id, "B", "")]

    if prefs.alpha_support:
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

###############################################################################
# HELPER FUNCTIONS
###############################################################################


def posterize(value, steps):
    return round(value * steps) / steps


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


def rgb_to_luminosity(color):
    # Y = 0.299 R + 0.587 G + 0.114 B
    return color[0] * 0.299 + color[1] * 0.587 + color[2] * 0.114


def convert_rgb_to_luminosity(mesh, src_vcol, dst_vcol, dst_channel_idx, dst_all_channels=False):
    if dst_all_channels:
        for loop_index, loop in enumerate(mesh.loops):
            luminosity = rgb_to_luminosity(src_vcol.data[loop_index].color)
            dst_vcol.data[loop_index].color = [luminosity] * 3
    else:
        for loop_index, loop in enumerate(mesh.loops):
            luminosity = rgb_to_luminosity(src_vcol.data[loop_index].color)
            dst_vcol.data[loop_index].color[dst_channel_idx] = luminosity


def copy_channel(mesh, src_vcol, dst_vcol, src_channel_idx, dst_channel_idx, swap=False, dst_all_channels=False):
    if dst_all_channels:
        for loop_index, loop in enumerate(mesh.loops):
            src_val = src_vcol.data[loop_index].color[src_channel_idx]
            dst_vcol.data[loop_index].color = [src_val] * 3
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


def get_validated_input(context, get_src, get_dst, src_is_weight=False, dst_is_weight=False):
    settings = context.scene.vertex_color_master_settings
    obj = context.active_object
    mesh = obj.data

    rv = {}

    message = None

    if not (src_is_weight and dst_is_weight) and mesh.vertex_colors is None:
        message = "Object has no vertex colors."

    if get_src and message is None:
        if not src_is_weight:
            if settings.src_vcol_id in mesh.vertex_colors:
                rv['src_vcol'] = mesh.vertex_colors[settings.src_vcol_id]
                rv['src_channel_idx'] = channel_id_to_idx(
                    settings.src_channel_id)
            else:
                message = "Src color layer is not valid."
        else:
            src_vgroup_idx = -1
            for group in obj.vertex_groups:
                if group.name == settings.src_vcol_id:
                    src_vgroup_idx = group.index
                    rv['src_vgroup_idx'] = src_vgroup_idx
                    break
            if src_vgroup_idx < 0:
                message = "Src vertex group is not valid."

    if get_dst and message is None:
        if not dst_is_weight:
            if settings.dst_vcol_id in mesh.vertex_colors:
                rv['dst_vcol'] = mesh.vertex_colors[settings.dst_vcol_id]
                rv['dst_channel_idx'] = channel_id_to_idx(
                    settings.dst_channel_id)
            else:
                message = "Dst color layer is not valid."
        else:
            dst_vgroup_idx = -1
            for group in obj.vertex_groups:
                if group.name == settings.dst_vcol_id:
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
        vi = get_validated_input(
            context, get_src=True, get_dst=True, dst_is_weight=True)

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
        vi = get_validated_input(
            context, get_src=True, get_dst=True, src_is_weight=True)

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

    value = bpy.props.FloatProperty(
        name="Value",
        default=1.0,
        min=0.0,
        max=1.0,
        description="Value to fill channel(s) with."
    )

    clear_inactive = bpy.props.BoolProperty(
        name="Clear Inactive",
        default=False,
        description="Clear inactive channel(s)."
    )

    clear_alpha = bpy.props.BoolProperty(
        name="Clear Alpha",
        default=False,
        description="Clear the alpha channel, even if not active and Clear Inactive is enabled."
    )

    def draw(self, context):
        prefs = context.user_preferences.addons[__name__].preferences
        layout = self.layout

        col = layout.column()
        col.prop(self, 'value', slider=True)
        col.prop(self, 'clear_inactive')
        if prefs.alpha_support and self.clear_inactive:
            col.prop(self, 'clear_alpha')

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return bpy.context.object.mode == 'VERTEX_PAINT' and obj is not None and obj.type == 'MESH'

    def execute(self, context):
        prefs = context.user_preferences.addons[__name__].preferences
        active_channels = context.scene.vertex_color_master_settings.active_channels
        mesh = context.active_object.data

        if mesh.vertex_colors:
            vcol_layer = mesh.vertex_colors.active
        else:
            vcol_layer = mesh.vertex_colors.new()

        value = self.value
        rmul = 1.0 if not self.clear_inactive or red_id in active_channels else 0.0
        gmul = 1.0 if not self.clear_inactive or green_id in active_channels else 0.0
        bmul = 1.0 if not self.clear_inactive or blue_id in active_channels else 0.0

        # TODO: would be best to detect alpha support automatically, like this, instead of using addon prefs
        alpha_enabled = prefs.alpha_support and len(vcol_layer.data[0].color) == 4

        if alpha_enabled:
            amul = 1.0 if not self.clear_inactive or not self.clear_alpha or alpha_id in active_channels else 0.0
            for loop_index, loop in enumerate(mesh.loops):
                color = vcol_layer.data[loop_index].color
                vcol_layer.data[loop_index].color = [
                    value if red_id in active_channels else color[0] * rmul,
                    value if green_id in active_channels else color[1] * gmul,
                    value if blue_id in active_channels else color[2] * bmul,
                    value if alpha_id in active_channels else color[3] * amul
                ]
        else:
            for loop_index, loop in enumerate(mesh.loops):
                color = vcol_layer.data[loop_index].color
                vcol_layer.data[loop_index].color = [
                    value if red_id in active_channels else color[0] * rmul,
                    value if green_id in active_channels else color[1] * gmul,
                    value if blue_id in active_channels else color[2] * bmul
                ]

        mesh.vertex_colors.active = vcol_layer
        mesh.update()

        return {'FINISHED'}


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
        active_channels = context.scene.vertex_color_master_settings.active_channels
        mesh = context.active_object.data

        if mesh.vertex_colors:
            vcol_layer = mesh.vertex_colors.active
        else:
            vcol_layer = mesh.vertex_colors.new()

        for loop_index, loop in enumerate(mesh.loops):
            color = vcol_layer.data[loop_index].color
            if red_id in active_channels:
                color[0] = 1 - color[0]
            if green_id in active_channels:
                color[1] = 1 - color[1]
            if blue_id in active_channels:
                color[2] = 1 - color[2]
            if alpha_id in active_channels:
                color[3] = 1 - color[3]
            vcol_layer.data[loop_index].color = color

        mesh.vertex_colors.active = vcol_layer
        mesh.update()

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
        active_channels = context.scene.vertex_color_master_settings.active_channels
        mesh = context.active_object.data

        if mesh.vertex_colors:
            vcol_layer = mesh.vertex_colors.active
        else:
            vcol_layer = mesh.vertex_colors.new()

        # using posterize(), 2 steps -> 3 tones, but best to have 2 steps -> 2 tones
        steps = self.steps - 1

        for loop_index, loop in enumerate(mesh.loops):
            color = vcol_layer.data[loop_index].color
            if red_id in active_channels:
                color[0] = posterize(color[0], steps)
            if green_id in active_channels:
                color[1] = posterize(color[1], steps)
            if blue_id in active_channels:
                color[2] = posterize(color[2], steps)
            if alpha_id in active_channels:
                color[3] = posterize(color[3], steps)
            vcol_layer.data[loop_index].color = color

        mesh.vertex_colors.active = vcol_layer
        mesh.update()

        return {'FINISHED'}


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


###############################################################################
# MAIN CLASS, UI, SETTINGS, PREFS AND REGISTRATION
###############################################################################

class VertexColorMasterAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    alpha_support = BoolProperty(
        name="Alpha Support",
        default=False,
        description="Enable support for vertex color alpha, available in some builds of Blender",
    )

    # use_own_tab = BoolProperty(
    #   name="Use Own Tab",
    #   default=False,
    #   description="Put add-on panel under its own tab, instead of under Tools"
    #   )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'alpha_support')


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
        update=update_active_channels,
    )

    match_brush_to_active_channels = BoolProperty(
        name="Match Active Channels",
        default=True,
        description="Change the brush color to match the active channels.",
        update=update_active_channels
    )

    def update_brush_value(self, context):
        if self.match_brush_to_active_channels:
            return update_active_channels(self, context)

        brush = bpy.data.brushes['Draw']
        color = Color(brush.color)
        color.v = self.brush_value
        brush.color = color

        return None

    brush_value = FloatProperty(
        name="Brush Value",
        description="Value of the brush color.",
        default=1.0,
        min=0.0,
        max=1.0,
        update=update_brush_value,
    )

    def vcol_layer_items(self, context):
        obj = context.active_object
        mesh = obj.data
        vertex_colors = [] if mesh.vertex_colors is None else [
            (vcol.name, vcol.name, '') for vcol in mesh.vertex_colors]
        vertex_groups = [(group.name, 'W: ' + group.name, '')
                         for group in obj.vertex_groups]
        vertex_colors.extend(vertex_groups)

        return vertex_colors

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
    bl_category = 'Tools'
    bl_context = 'vertexpaint'

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        settings = context.scene.vertex_color_master_settings

        # Brush Settings
        brush = bpy.data.brushes['Draw']
        col = layout.column(align=True)
        row = col.row()
        row.label('Brush Settings')
        row = col.row(align=True)
        row.prop(brush, 'color', text="")
        row.prop(settings, 'brush_value', 'Val', slider=True)

        col = layout.column(align=True)
        row = col.row()
        row.prop(settings, 'match_brush_to_active_channels')
        row = col.row(align=True)
        blend_mode_name = ''
        for mode in brush_blend_mode_items:
            if mode[0] == brush.vertex_tool:
                blend_mode_name = mode[1]
        row.label('Brush Mode: {0}'.format(blend_mode_name))
        row = col.row(align=True)
        row.operator('vertexcolormaster.edit_brush_settings', "Mix").blend_mode = 'MIX'
        row.operator('vertexcolormaster.edit_brush_settings', "Add").blend_mode = 'ADD'
        row.operator('vertexcolormaster.edit_brush_settings', "Subtract").blend_mode = 'SUB'
        row = col.row(align=True)
        row.operator('vertexcolormaster.edit_brush_settings', "Lighten").blend_mode = 'LIGHTEN'
        row.operator('vertexcolormaster.edit_brush_settings', "Darken").blend_mode = 'DARKEN'
        row = col.row(align=True)
        row.operator('vertexcolormaster.edit_brush_settings', "Multiply").blend_mode = 'MUL'
        row.operator('vertexcolormaster.edit_brush_settings', "Blur").blend_mode = 'BLUR'

        layout.separator()

        # Active Channel Operations
        col = layout.column(align=True)
        row = col.row()
        row.label('Active Channels')
        row = col.row()
        row.prop(settings, 'active_channels', expand=True)

        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator('vertexcolormaster.fill', 'Fill').value = 1.0
        row.operator('vertexcolormaster.fill', 'Clear').value = 0.0
        row = col.row(align=True)
        row.operator('vertexcolormaster.invert', 'Invert')
        row.operator('vertexcolormaster.posterize', 'Posterize')

        layout.separator()

        # Source->Destination Channel Operations
        col = layout.column(align=True)
        row = col.row()
        row.label('Channel/Weights Transfer')
        src_is_vg = settings.src_vcol_id in obj.vertex_groups
        dst_is_vg = settings.dst_vcol_id in obj.vertex_groups

        lcol_percentage = 0.8
        row = layout.row()
        split = row.split(lcol_percentage, align=True)
        col = split.column(align=True)
        col.prop(settings, 'src_vcol_id', 'Src')
        split = split.split(align=True)
        col = split.column(align=True)
        col.prop(settings, 'src_channel_id', '')
        col.enabled = not src_is_vg

        row = layout.row()
        split = row.split(lcol_percentage, align=True)
        col = split.column(align=True)
        col.prop(settings, 'dst_vcol_id', 'Dst')
        split = split.split(align=True)
        col = split.column(align=True)
        col.prop(settings, 'dst_channel_id', '')
        col.enabled = not dst_is_vg

        if not (src_is_vg or dst_is_vg):
            row = layout.row(align=True)
            row.operator('vertexcolormaster.copy_channel',
                         'Copy').swap_channels = False
            row.operator('vertexcolormaster.copy_channel',
                         'Swap').swap_channels = True

            col = layout.column(align=True)
            row = col.row()
            row.operator('vertexcolormaster.blend_channels',
                         'Blend').blend_mode = settings.channel_blend_mode
            row.prop(settings, 'channel_blend_mode', '')

            col = layout.column(align=True)
            row = col.row(align=True)
            row.operator('vertexcolormaster.rgb_to_grayscale',
                         'Src RGB to luminosity')
            row = col.row(align=True)
            row.operator('vertexcolormaster.copy_channel', 'Src ({0}) to Dst RGB'.format(
                settings.src_channel_id)).all_channels = True
        elif src_is_vg and not dst_is_vg:
            row = layout.row(align=True)
            row.operator('vertexcolormaster.weights_to_color',
                         'Weights to Dst ({0})'.format(settings.src_channel_id))
        elif dst_is_vg and not src_is_vg:
            row = layout.row(align=True)
            row.operator('vertexcolormaster.color_to_weights',
                         'Src ({0}) to Weights'.format(settings.src_channel_id))
        # else: # src_is_vg and dst_is_vg


###############################################################################
# OPERATOR REGISTRATION
###############################################################################

def register():
    bpy.utils.register_class(VertexColorMasterAddonPreferences)
    bpy.utils.register_class(VertexColorMasterProperties)
    bpy.types.Scene.vertex_color_master_settings = PointerProperty(
        type=VertexColorMasterProperties)

    bpy.utils.register_class(VertexColorMaster)
    bpy.utils.register_class(VertexColorMaster_Fill)
    bpy.utils.register_class(VertexColorMaster_Invert)
    bpy.utils.register_class(VertexColorMaster_Posterize)
    bpy.utils.register_class(VertexColorMaster_CopyChannel)
    bpy.utils.register_class(VertexColorMaster_RgbToGrayscale)
    bpy.utils.register_class(VertexColorMaster_BlendChannels)
    bpy.utils.register_class(VertexColorMaster_EditBrushSettings)
    bpy.utils.register_class(VertexColorMaster_WeightsToColor)
    bpy.utils.register_class(VertexColorMaster_ColorToWeights)


def unregister():
    bpy.utils.unregister_class(VertexColorMasterAddonPreferences)
    bpy.utils.unregister_class(VertexColorMasterProperties)
    del bpy.types.Scene.vertex_color_master_settings

    bpy.utils.unregister_class(VertexColorMaster)
    bpy.utils.unregister_class(VertexColorMaster_Fill)
    bpy.utils.unregister_class(VertexColorMaster_Invert)
    bpy.utils.unregister_class(VertexColorMaster_Posterize)
    bpy.utils.unregister_class(VertexColorMaster_CopyChannel)
    bpy.utils.unregister_class(VertexColorMaster_RgbToGrayscale)
    bpy.utils.unregister_class(VertexColorMaster_BlendChannels)
    bpy.utils.unregister_class(VertexColorMaster_EditBrushSettings)
    bpy.utils.unregister_class(VertexColorMaster_WeightsToColor)
    bpy.utils.unregister_class(VertexColorMaster_ColorToWeights)


# allows running addon from text editor
if __name__ == '__main__':
    register()
