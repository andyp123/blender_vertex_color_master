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
import math
from bpy.props import *
from .vcm_globals import *
from .vcm_helpers import *
from mathutils import Color, Vector, Matrix

# import copy # for copying data structures
import bmesh # for random color to mesh islands
import random # for random color to mesh islands

# # for gradient tool
import gpu # used for drawing lines
from gpu_extras.batch import batch_for_shader
from bpy_extras import view3d_utils

def draw_gradient_callback(self, context, line_params, line_shader, circle_shader):
    line_batch = batch_for_shader(line_shader, 'LINES', {
        "pos": line_params["coords"],
        "color": line_params["colors"]})
    line_shader.bind()
    line_batch.draw(line_shader)

    if circle_shader is not None:
        a = line_params["coords"][0]
        b = line_params["coords"][1]
        radius = (b - a).length
        steps = 50
        circle_points = []
        for i in range(steps+1):
            angle = (2.0 * math.pi * i) / steps
            point = Vector((a.x + radius * math.cos(angle), a.y + radius * math.sin(angle)))
            circle_points.append(point)

        circle_batch = batch_for_shader(circle_shader, 'LINE_LOOP', {
            "pos": circle_points})
        circle_shader.bind()
        circle_shader.uniform_float("color", line_params["colors"][1])
        circle_batch.draw(circle_shader)


# This function from a script by Bartosz Styperek with modifications by me
# Circular gradient based on code submitted by RylauChelmi
class VERTEXCOLORMASTER_OT_Gradient(bpy.types.Operator):
    """Draw a line with the mouse to paint a vertex color gradient"""
    bl_idname = "vertexcolormaster.gradient"
    bl_label = "VCM Gradient Tool"
    bl_description = "Paint vertex color gradient."
    bl_options = {"REGISTER", "UNDO"}

    _handle = None

    line_shader = gpu.shader.from_builtin('2D_SMOOTH_COLOR')
    circle_shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')

    start_color: FloatVectorProperty(
        name="Start Color",
        subtype='COLOR',
        default=[1.0,0.0,0.0],
        description="Start color of the gradient."
    )

    end_color: FloatVectorProperty(
        name="End Color",
        subtype='COLOR',
        default=[0.0,1.0,0.0],
        description="End color of the gradient."
    )

    circular_gradient: BoolProperty(
        name="Circular Gradient",
        description="Paint a circular gradient",
        default=False
    )

    use_hue_blend: BoolProperty(
        name="Use Hue Blend",
        description="Gradually blend start and end colors using full hue range instead of simple blend",
        default=False
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return bpy.context.object.mode == 'VERTEX_PAINT' and obj is not None and obj.type == 'MESH'

    def paintVerts(self, context, start_point, end_point, start_color, end_color, circular_gradient=False, use_hue_blend=False):
        region = context.region
        rv3d = context.region_data

        obj = context.active_object
        mesh = obj.data

        # Create a new bmesh to work with
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()

        # List of structures containing 3d vertex and project 2d position of vertex
        vertex_data = None # Will contain vert, and vert coordinates in 2d view space
        if mesh.use_paint_mask_vertex: # Face masking not currently supported
            vertex_data = [(v, view3d_utils.location_3d_to_region_2d(region, rv3d, obj.matrix_world @ v.co)) for v in bm.verts if v.select]
        else:
            vertex_data = [(v, view3d_utils.location_3d_to_region_2d(region, rv3d, obj.matrix_world @ v.co)) for v in bm.verts]

        # Vertex transformation math
        down_vector = Vector((0, -1, 0))
        direction_vector = Vector((end_point.x - start_point.x, end_point.y - start_point.y, 0)).normalized()
        rotation = direction_vector.rotation_difference(down_vector)

        translation_matrix = Matrix.Translation(Vector((-start_point.x, -start_point.y, 0)))
        inverse_translation_matrix = translation_matrix.inverted()
        rotation_matrix = rotation.to_matrix().to_4x4()
        combinedMat = inverse_translation_matrix @ rotation_matrix @ translation_matrix

        transStart = combinedMat @ start_point.to_4d() # Transform drawn line : rotate it to align to horizontal line
        transEnd = combinedMat @ end_point.to_4d()
        minY = transStart.y
        maxY = transEnd.y
        heightTrans = maxY - minY  # Get the height of transformed vector

        transVector = transEnd - transStart
        transLen = transVector.length

        # Calculate hue, saturation and value shift for blending
        if use_hue_blend:
            start_color = Color(start_color[:3])
            end_color = Color(end_color[:3])
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
            transVec = combinedMat @ vertCo4d

            t = 0

            if circular_gradient:
                curVector = transVec.to_4d() - transStart
                curLen = curVector.length
                t = abs(max(min(curLen / transLen, 1), 0))
            else:
                t = abs(max(min((transVec.y - minY) / heightTrans, 1), 0))

            color = Color((1, 0, 0))
            if use_hue_blend:
                # Hue wraps, and fmod doesn't work with negative values
                color.h = fmod(1.0 + c1_hue + hue_separation * t, 1.0) 
                color.s = c1_sat + sat_separation * t
                color.v = c1_val + val_separation * t
            else:
                color.r = start_color[0] + (end_color[0] - start_color[0]) * t
                color.g = start_color[1] + (end_color[1] - start_color[1]) * t
                color.b = start_color[2] + (end_color[2] - start_color[2]) * t

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

        # Begin gradient line and initialize draw handler
        if self._handle is None:
            if event.type == 'LEFTMOUSE':
                # Store the foreground and background color for redo
                brush = bpy.data.brushes['Draw']
                self.start_color = brush.color
                self.end_color = brush.secondary_color

                # Create arguments to pass to the draw handler callback
                mouse_position = Vector((event.mouse_region_x, event.mouse_region_y))
                self.line_params = {
                    "coords": [mouse_position, mouse_position],
                    "colors": [brush.color[:] + (1.0,),
                               brush.secondary_color[:] + (1.0,)],
                    "width": 1, # currently does nothing
                }
                args = (self, context, self.line_params, self.line_shader,
                    (self.circle_shader if self.circular_gradient else None))
                self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_gradient_callback, args, 'WINDOW', 'POST_PIXEL')
        else:
            # Update or confirm gradient end point
            if event.type in {'MOUSEMOVE', 'LEFTMOUSE'}:
                line_params = self.line_params
                delta = 20

                # Update and constrain end point
                start_point = line_params["coords"][0]
                end_point = Vector((event.mouse_region_x, event.mouse_region_y))
                if event.shift:
                    end_point = self.axis_snap(start_point, end_point, delta)
                line_params["coords"] = [start_point, end_point]

                if event.type == 'LEFTMOUSE' and end_point != start_point: # Finish updating the line and paint the vertices
                    bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
                    self._handle = None

                    # Gradient will not work if there is no delta
                    if end_point == start_point:
                        return {'CANCELLED'}

                    # Use color gradient or force grayscale in isolate mode
                    start_color = line_params["colors"][0]
                    end_color = line_params["colors"][1]
                    isolate = get_isolated_channel_ids(context.active_object.data.vertex_colors.active)
                    use_hue_blend = self.use_hue_blend
                    if isolate is not None:
                        start_color = [rgb_to_luminosity(start_color)] * 3
                        end_color = [rgb_to_luminosity(end_color)] * 3
                        use_hue_blend = False

                    self.paintVerts(context, start_point, end_point, start_color, end_color, self.circular_gradient, use_hue_blend)
                    return {'FINISHED'}            

        # Allow camera navigation
        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            return {'PASS_THROUGH'}

        if event.type in {'RIGHTMOUSE', 'ESC'}:
            if self._handle is not None:
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
                self._handle = None
            return {'CANCELLED'}

        # Keep running until completed or cancelled
        return {'RUNNING_MODAL'}

    def execute(self, context):
        start_point = self.line_params["coords"][0]
        end_point = self.line_params["coords"][1]
        start_color = self.start_color
        end_color = self.end_color

        # Use color gradient or force grayscale in isolate mode
        isolate = get_isolated_channel_ids(context.active_object.data.vertex_colors.active)
        use_hue_blend = self.use_hue_blend
        if isolate is not None:
            start_color = [rgb_to_luminosity(start_color)] * 3
            end_color = [rgb_to_luminosity(end_color)] * 3
            use_hue_blend = False

        self.paintVerts(context, start_point, end_point, start_color, end_color, self.circular_gradient, use_hue_blend)

        return {'FINISHED'}

    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}


# Partly based on code by Bartosz Styperek
class VERTEXCOLORMASTER_OT_RandomizeMeshIslandColors(bpy.types.Operator):
    """Assign random colors to separate mesh islands"""
    bl_idname = 'vertexcolormaster.randomize_mesh_island_colors'
    bl_label = 'VCM Randomize Mesh Island Colors'
    bl_options = {'REGISTER', 'UNDO'}

    random_seed: IntProperty(
        name="Random Seed",
        description="Seed for the randomization. Change this value to get different random colors.",
        default=1,
        min=1,
        max=1000
    )

    randomize_hue: BoolProperty(
        name="Randmize Hue",
        description="Randomize Hue",
        default=True
    )

    randomize_saturation: BoolProperty(
        name="Randmize Saturation",
        description="Randomize Saturation",
        default=False
    )

    randomize_value: BoolProperty(
        name="Randmize Value",
        description="Randomize Value",
        default=False
    )

    base_hue: FloatProperty(
        name="Hue",
        description="When not randomized, the hue will be set to this value.",
        default=0.0,
        min=0.0,
        max=1.0
    )

    base_saturation: FloatProperty(
        name="Saturation",
        description="When not randomized, the saturation will be set to this value.",
        default=1.0,
        min=0.0,
        max=1.0
    )

    base_value: FloatProperty(
        name="Value",
        description="When not randomized, the value will be set to this value.",
        default=1.0,
        min=0.0,
        max=1.0
    )

    order_based: BoolProperty(
        name="Order Based",
        description="The colors assigned will be based on the number of islands. Not truly random, but maximum color separation.",
        default=False
    )

    merge_similar: BoolProperty(
        name="Merge Similar",
        description="Use the same color for similar parts of the mesh (determined by equal face count).",
        default=False
    )

    # Use custom UI for better showing randomization parameters
    def draw(self, context):
        layout = self.layout

        layout.label(text="Randomization Parameters")

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(self, 'randomize_hue', text="Randomize")
        row.prop(self, 'base_hue', text="H", slider=True)
        row = col.row(align=True)
        row.prop(self, 'randomize_saturation', text="Randomize")
        row.prop(self, 'base_saturation', text="S", slider=True)
        row = col.row(align=True)
        row.prop(self, 'randomize_value', text="Randomize")
        row.prop(self, 'base_value', text="V", slider=True)

        layout.prop(self, 'random_seed', text="Seed", slider=True)

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

        # If we are in isolate mode, this is used to force greyscale
        isolate = get_isolated_channel_ids(context.active_object.data.vertex_colors.active)

        for index, island in enumerate(mesh_islands):
            color = Color((1, 0, 0)) # (0, 1, 1) HSV

            # Determine color based on settings
            if self.merge_similar:
                face_count = len(island)
                if face_count in island_colors.keys():
                    color = island_colors[face_count]
                else:
                    if isolate is not None:
                        v = random.random()
                        color = Color((v, v, v))
                        island_colors[face_count] = color
                    else:
                        color.h = random.random() if self.randomize_hue else self.base_hue
                        color.s = random.random() if self.randomize_saturation else self.base_saturation
                        color.v = random.random() if self.randomize_value else self.base_value
                        island_colors[face_count] = color
            else:
                if isolate is not None:
                    v = index * separationDiff if self.order_based else random.random()
                    color = Color((v, v, v))
                else:
                    if self.order_based:
                        color.h = index * separationDiff if self.randomize_hue else self.base_hue
                        color.s = index * separationDiff if self.randomize_saturation else self.base_saturation
                        color.v = index * separationDiff if self.randomize_value else self.base_value
                    else:
                        color.h = random.random() if self.randomize_hue else self.base_hue
                        color.s = random.random() if self.randomize_saturation else self.base_saturation
                        color.v = random.random() if self.randomize_value else self.base_value

            # Set island face colors
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


class VERTEXCOLORMASTER_OT_BlurChannel(bpy.types.Operator):
    """Blur values of a particular channel"""
    bl_idname = 'vertexcolormaster.blur_channel'
    bl_label = 'VCM Blur Channel'
    bl_options = {'REGISTER', 'UNDO'}

    factor: FloatProperty(
        name="Factor",
        description="Amount of blur to apply.",
        default=0.5,
        min=0.0,
        max=1.0
    )  

    iterations: IntProperty(
        name="Iterations",
        description="Number of iterations to blur values.",
        default=1,
        min=1,
        max=200
    ) 

    expand: FloatProperty(
        name="Expand/Contract",
        description="Alter how the blur affects the distribution of dark/light values.",
        default=0.0,
        min=-1.0,
        max=1.0
    ) 

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return bpy.context.object.mode == 'VERTEX_PAINT' and obj is not None and obj.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        mesh = obj.data
        vcol = mesh.vertex_colors.active if mesh.vertex_colors else mesh.vertex_colors.new()
        isolate = get_isolated_channel_ids(vcol)

        if isolate is None:
            self.report({'ERROR'}, "Blur only works with an isolated channel")
            return {'CANCELLED'}

        vgroup_id = 'vcm_temp_weights'
        vgroup = obj.vertex_groups.new(name=vgroup_id)
        obj.vertex_groups.active_index = vgroup.index

        channel_idx = channel_id_to_idx(isolate[1])
        color_to_weights(obj, vcol, channel_idx, vgroup.index)

        bpy.ops.object.mode_set(mode='WEIGHT_PAINT', toggle=False)
        bpy.ops.object.vertex_group_smooth(
            group_select_mode='ACTIVE',
            factor=self.factor,
            repeat=self.iterations,
            expand=self.expand
        )
        bpy.ops.object.mode_set(mode='VERTEX_PAINT', toggle=False)

        weights_to_color(mesh, vgroup.index, vcol, channel_idx, all_channels=True)

        obj.vertex_groups.remove(vgroup)

        return {'FINISHED'}


class VERTEXCOLORMASTER_OT_ColorToUVs(bpy.types.Operator):
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


class VERTEXCOLORMASTER_OT_UVsToColor(bpy.types.Operator):
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


class VERTEXCOLORMASTER_OT_ColorToWeights(bpy.types.Operator):
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


class VERTEXCOLORMASTER_OT_WeightsToColor(bpy.types.Operator):
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


class VERTEXCOLORMASTER_OT_RgbToGrayscale(bpy.types.Operator):
    """Convert the RGB color of a vertex color layer to a grayscale value"""
    bl_idname = 'vertexcolormaster.rgb_to_grayscale'
    bl_label = 'VCM RGB to grayscale'
    bl_options = {'REGISTER', 'UNDO'}

    all_channels: bpy.props.BoolProperty(
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


class VERTEXCOLORMASTER_OT_CopyChannel(bpy.types.Operator):
    """Copy or swap channel data from one channel to another"""
    bl_idname = 'vertexcolormaster.copy_channel'
    bl_label = 'VCM Copy channel data'
    bl_options = {'REGISTER', 'UNDO'}

    swap_channels: bpy.props.BoolProperty(
        name="Swap Channels",
        default=False,
        description="Swap source and destination channels instead of copying."
    )

    all_channels: bpy.props.BoolProperty(
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


class VERTEXCOLORMASTER_OT_BlendChannels(bpy.types.Operator):
    """Blend source and destination channels (result is saved in destination)"""
    bl_idname = 'vertexcolormaster.blend_channels'
    bl_label = 'VCM Blend Channels'
    bl_options = {'REGISTER', 'UNDO'}

    blend_mode: bpy.props.EnumProperty(
        name="Blend Mode",
        items=channel_blend_mode_items,
        description="Blending operation used when the Src and Dst channels are blended.",
        default='ADD'
    )

    result_channel_id: EnumProperty(
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


class VERTEXCOLORMASTER_OT_Fill(bpy.types.Operator):
    """Fill the active vertex color channel(s)"""
    bl_idname = 'vertexcolormaster.fill'
    bl_label = 'VCM Fill'
    bl_options = {'REGISTER', 'UNDO'}

    value: FloatProperty(
        name="Value",
        description="Value to fill active channel(s) with.",
        default=1.0,
        min=0.0,
        max=1.0
    )

    fill_with_color: BoolProperty(
        name="Fill with Color",
        description="Ignore active channels and fill with an RGB color",
        default=False
    )

    fill_color: FloatVectorProperty(
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
            row.prop(self, 'fill_color', text="")


class VERTEXCOLORMASTER_OT_Invert(bpy.types.Operator):
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


class VERTEXCOLORMASTER_OT_Posterize(bpy.types.Operator):
    """Posterize active vertex color channel(s)"""
    bl_idname = 'vertexcolormaster.posterize'
    bl_label = 'VCM Posterize'
    bl_options = {'REGISTER', 'UNDO'}

    steps: bpy.props.IntProperty(
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


class VERTEXCOLORMASTER_OT_Remap(bpy.types.Operator):
    """Remap active vertex color channel(s)"""
    bl_idname = 'vertexcolormaster.remap'
    bl_label = 'VCM Remap'
    bl_options = {'REGISTER', 'UNDO'}

    min0: FloatProperty(
        default=0,
        min=0,
        max=1
    )

    max0: FloatProperty(
        default=1,
        min=0,
        max=1
    )

    min1: FloatProperty(
        default=0,
        min=0,
        max=1
    )

    max1: FloatProperty(
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

        layout.label(text="Input Range")
        layout.prop(self, 'min0', text="Min", slider=True)
        layout.prop(self, 'max0', text="Max", slider=True)

        layout.label(text="Output Range")
        layout.prop(self, 'min1', text="Min", slider=True)
        layout.prop(self, 'max1', text="Max", slider=True)


class VERTEXCOLORMASTER_OT_EditBrushSettings(bpy.types.Operator):
    """Set vertex paint brush settings"""
    bl_idname = 'vertexcolormaster.edit_brush_settings'
    bl_label = 'VCM Edit Brush Settings'
    bl_options = {'REGISTER', 'UNDO'}

    blend_mode: EnumProperty(
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
         # This changed between Blender 2.79 -> 2.80, but keeping blur here
        if self.blend_mode == 'BLUR':
            brush.vertex_tool = 'BLUR'
            brush.blend = 'MIX'
        else:
            brush.vertex_tool = 'DRAW'
            brush.blend = self.blend_mode

        return {'FINISHED'}


class VERTEXCOLORMASTER_OT_QuickFill(bpy.types.Operator):
    """Quick fill vertex color RGB with current brush color. Can use selection mask"""
    bl_idname = 'vertexcolormaster.quick_fill'
    bl_label = 'VCM Fill Color'
    bl_options = {'REGISTER', 'UNDO'}

    fill_color: FloatVectorProperty(
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


class VERTEXCOLORMASTER_OT_IsolateChannel(bpy.types.Operator):
    """Isolate a specific channel to paint in grayscale"""
    bl_idname = 'vertexcolormaster.isolate_channel'
    bl_label = 'VCM Isolate Channel'
    bl_options = {'REGISTER', 'UNDO'}

    src_channel_id: EnumProperty(
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
        settings.brush_secondary_color = brush.secondary_color
        brush.color = [settings.brush_value_isolate] * 3
        brush.secondary_color = [settings.brush_secondary_value_isolate] * 3

        return {'FINISHED'}


class VERTEXCOLORMASTER_OT_ApplyIsolatedChannel(bpy.types.Operator):
    """Apply isolated channel back to the vertex color layer it came from"""
    bl_idname = 'vertexcolormaster.apply_isolated'
    bl_label = "VCM Apply Isolated Channel"
    bl_options = {'REGISTER', 'UNDO'}

    discard: BoolProperty(
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
        brush.secondary_color = settings.brush_secondary_color

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


# This also supports value flipping, but otherwise can be# replaced in UI with paint.brush_colors_flip
class VERTEXCOLORMASTER_OT_FlipBrushColors(bpy.types.Operator):
    """Toggle foreground and background brush colors"""
    bl_idname = 'vertexcolormaster.brush_colors_flip'
    bl_label = "VCM Flip Brush Colors"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return bpy.context.object.mode == 'VERTEX_PAINT'

    def execute(self, context):
        brush = bpy.data.brushes['Draw']
        settings = context.scene.vertex_color_master_settings

        obj = context.active_object
        if context.object.mode == 'VERTEX_PAINT' and obj is not None and obj.type == 'MESH' \
            and get_isolated_channel_ids(context.active_object.data.vertex_colors.active) is not None \
            or settings.use_grayscale:
                v1 = settings.brush_value_isolate
                v2 = settings.brush_secondary_value_isolate
                settings.brush_value_isolate = v2
                settings.brush_secondary_value_isolate = v1
                brush.color = Color((v2, v2, v2))
                brush.secondary_color = Color((v1, v1, v1))
        else:
            color = Color(brush.color)
            brush.color = brush.secondary_color
            brush.secondary_color = color

        return {'FINISHED'}