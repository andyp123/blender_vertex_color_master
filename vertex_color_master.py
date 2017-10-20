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
# + operate on selection only (VERT/EDGE, FACE)
# + convert to weights
# + quick channel preview / view as greyscale / isolate
# + implement support for alpha (see recent vertex painting commits and try with build)
# + massive code cleanup

# CLEANUP TODO:
# move input evaluation code out of helpers to operators
# clean up context.scene.[my_variable] stuff and put in correct place
# optimisation such as getting rid of append operations if array size is known

import bpy
from bpy.props import (
        StringProperty,
        BoolProperty,
        FloatProperty,
        EnumProperty,
        )

bl_info = {
  "name": "Vertex Color Master",
  "author": "Andrew Palmer",
  "version": (0, 0, 1),
  "blender": (2, 79, 0),
  "location": "",
  "description": "Tools for working with vertex colors at greater precision than using the paint brush.",
  "category": "Paint"
}

red_id = 'R'
green_id = 'G'
blue_id = 'B'
alpha_id = 'A'

channel_items = ((red_id, "R", ""), (green_id, "G", ""), (blue_id, "B", ""))#, (alpha_id, "A", ""))

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

##### HELPER FUNCTIONS #####
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
  return color[0]*0.299 + color[1]*0.587 + color[2]*0.114


def convert_rgb_to_luminosity(mesh, src_vcol_id, dst_vcol_id, dst_channel_idx, dst_all_channels=False):
  # validate input
  if mesh.vertex_colors is None:
    print("mesh has no vertex colors")
    return
  src_vcol = None if src_vcol_id not in mesh.vertex_colors else mesh.vertex_colors[src_vcol_id]
  dst_vcol = None if dst_vcol_id not in mesh.vertex_colors else mesh.vertex_colors[dst_vcol_id]

  if src_vcol is None or dst_vcol is None:
    print("source or destination are invalid")
    return

  # convert color to luminosity
  if dst_all_channels:
    for loop_index, loop in enumerate(mesh.loops):
      luminosity = rgb_to_luminosity(src_vcol.data[loop_index].color)
      dst_vcol.data[loop_index].color = [luminosity]*3
  else:
    for loop_index, loop in enumerate(mesh.loops):
      luminosity = rgb_to_luminosity(src_vcol.data[loop_index].color)
      dst_vcol.data[loop_index].color[dst_channel_idx] = luminosity


def copy_channel(mesh, src_vcol_id, dst_vcol_id, src_channel_idx, dst_channel_idx, swap=False, dst_all_channels=False):
  # validate input
  if mesh.vertex_colors is None:
    print("mesh has no vertex colors")
    return
  src_vcol = None if src_vcol_id not in mesh.vertex_colors else mesh.vertex_colors[src_vcol_id]
  dst_vcol = None if dst_vcol_id not in mesh.vertex_colors else mesh.vertex_colors[dst_vcol_id]

  if src_vcol is None or dst_vcol is None:
    print("source or destination are invalid")
    return

  if dst_all_channels:
    for loop_index, loop in enumerate(mesh.loops):
      src_val = src_vcol.data[loop_index].color[src_channel_idx]
      dst_vcol.data[loop_index].color = [src_val]*3
  else:
    if src_vcol == dst_vcol and src_channel_idx == dst_channel_idx:
      print("source and destination are the same")
      return

    # perfrom channel copy/swap
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


def blend_channels(mesh, src_vcol_id, dst_vcol_id, src_channel_idx, dst_channel_idx, result_channel_idx, operation='Add'):
    # validate input
  if mesh.vertex_colors is None:
    print("mesh has no vertex colors")
    return
  src_vcol = None if src_vcol_id not in mesh.vertex_colors else mesh.vertex_colors[src_vcol_id]
  dst_vcol = None if dst_vcol_id not in mesh.vertex_colors else mesh.vertex_colors[dst_vcol_id]

  if src_vcol is None or dst_vcol is None:
    print("source or destination are invalid")
    return

  if operation == 'Add':
    for loop_index, loop in enumerate(mesh.loops):
      val = src_vcol.data[loop_index].color[src_channel_idx] + dst_vcol.data[loop_index].color[dst_channel_idx]
      dst_vcol.data[loop_index].color[result_channel_idx] = max(0.0, min(val, 1.0)) # clamp
  elif operation == 'Subtract':
    for loop_index, loop in enumerate(mesh.loops):
      val = src_vcol.data[loop_index].color[src_channel_idx] - dst_vcol.data[loop_index].color[dst_channel_idx]
      dst_vcol.data[loop_index].color[result_channel_idx] = max(0.0, min(val, 1.0)) # clamp
  elif operation == 'Multiply':
    for loop_index, loop in enumerate(mesh.loops):
      val = src_vcol.data[loop_index].color[src_channel_idx] * dst_vcol.data[loop_index].color[dst_channel_idx]
      dst_vcol.data[loop_index].color[result_channel_idx] = val
  elif operation == 'Divide':
    for loop_index, loop in enumerate(mesh.loops):
      src = src_vcol.data[loop_index].color[src_channel_idx]
      dst = dst_vcol.data[loop_index].color[dst_channel_idx]
      val = 0.0 if src == 0.0 else 1.0 if dst == 0.0 else src / dst
      dst_vcol.data[loop_index].color[result_channel_idx] = val
  elif operation == 'Lighten':
    for loop_index, loop in enumerate(mesh.loops):
      src = src_vcol.data[loop_index].color[src_channel_idx]
      dst = dst_vcol.data[loop_index].color[dst_channel_idx]
      dst_vcol.data[loop_index].color[result_channel_idx] = src if src > dst else dst
  elif operation == 'Darken':
    for loop_index, loop in enumerate(mesh.loops):
      src = src_vcol.data[loop_index].color[src_channel_idx]
      dst = dst_vcol.data[loop_index].color[dst_channel_idx]
      dst_vcol.data[loop_index].color[result_channel_idx] = src if src < dst else dst
  elif operation == 'Mix':
    for loop_index, loop in enumerate(mesh.loops):
      dst_vcol.data[loop_index].color[result_channel_idx] = src_vcol.data[loop_index].color[src_channel_idx]
  else:
    return

  mesh.update()


def weights_to_color(mesh, src_vgroup_idx, dst_vcol, dst_channel_idx):
  vertex_weights = [0.0]*len(mesh.vertices)

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
  # use this to create an average when setting weights
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

  return



##### MAIN OPERATOR CLASSES #####
class VertexColorMaster_ColorToWeights(bpy.types.Operator):
  """Copy vertex color channel to vertex group weights"""
  bl_idname = 'vertexcolormaster.color_to_weights'
  bl_label = 'VCM Color to weights'
  bl_options = {'REGISTER', 'UNDO'}

  @classmethod
  def poll(cls, context):
    active_obj = context.active_object
    return active_obj != None and active_obj.type == 'MESH'

  def execute(self, context):
    obj = context.active_object
    mesh = obj.data

    # validate input
    if mesh.vertex_colors is None:
      return {'FINISHED'}
    src_vcol_id = context.scene.src_vcol_id
    if src_vcol_id not in mesh.vertex_colors:
      return {'FINISHED'}
    src_vcol = mesh.vertex_colors[src_vcol_id]
    src_channel_idx = channel_id_to_idx(context.scene.src_channel_id)

    # get correct vertex group index
    dst_group_id = context.scene.dst_vcol_id
    dst_vgroup_idx = -1
    for group in obj.vertex_groups:
      if group.name == dst_group_id:
        dst_vgroup_idx = group.index
        break
    if dst_vgroup_idx < 0:
      return {'FINISHED'}

    color_to_weights(obj, src_vcol, src_channel_idx, dst_vgroup_idx)

    return {'FINISHED'}


class VertexColorMaster_WeightsToColor(bpy.types.Operator):
  """Copy vertex group weights to vertex color channel"""
  bl_idname = 'vertexcolormaster.weights_to_color'
  bl_label = 'VCM Weights to color'
  bl_options = {'REGISTER', 'UNDO'}

  @classmethod
  def poll(cls, context):
    active_obj = context.active_object
    return active_obj != None and active_obj.type == 'MESH'

  def execute(self, context):
    obj = context.active_object
    mesh = obj.data

    # validate input
    if mesh.vertex_colors is None:
      return {'FINISHED'}
    dst_vcol_id = context.scene.dst_vcol_id
    if dst_vcol_id not in mesh.vertex_colors:
      return {'FINISHED'}
    dst_vcol = mesh.vertex_colors[dst_vcol_id]
    dst_channel_idx = channel_id_to_idx(context.scene.dst_channel_id)

    # get correct vertex group index
    src_group_id = context.scene.src_vcol_id
    src_vgroup_idx = -1
    for group in obj.vertex_groups:
      if group.name == src_group_id:
        src_vgroup_idx = group.index
        break
    if src_vgroup_idx < 0:
      return {'FINISHED'}

    weights_to_color(mesh, src_vgroup_idx, dst_vcol, dst_channel_idx)

    return {'FINISHED'}


class VertexColorMaster_RgbToGrayscale(bpy.types.Operator):
  """Convert the RGB color of a vertex color layer to a grayscale value"""
  bl_idname = 'vertexcolormaster.rgb_to_grayscale'
  bl_label = 'VCM RGB to grayscale'
  bl_options = {'REGISTER', 'UNDO'}

  all_channels = bpy.props.BoolProperty(
    name = "all channels",
    default = True,
    description = "Put the grayscale value in all channels of the destination"
    )

  @classmethod
  def poll(cls, context):
    active_obj = context.active_object
    return active_obj != None and active_obj.type == 'MESH'

  def execute(self, context):
    src_id = context.scene.src_vcol_id
    dst_id = context.scene.dst_vcol_id
    dst_channel_idx = channel_id_to_idx(context.scene.dst_channel_id)
    mesh = context.active_object.data

    convert_rgb_to_luminosity(mesh, src_id, dst_id, dst_channel_idx, self.all_channels)

    return {'FINISHED'}


class VertexColorMaster_CopyChannel(bpy.types.Operator):
  """Copy or swap channel data from one channel to another"""
  bl_idname = 'vertexcolormaster.copy_channel'
  bl_label = 'VCM Copy channel data'
  bl_options = {'REGISTER', 'UNDO'}

  swap_channels = bpy.props.BoolProperty(
    name = "swap channels",
    default = False,
    description = "Swap source and destination channels instead of copy"
    )

  all_channels = bpy.props.BoolProperty(
    name = "all channels",
    default = False,
    description = "Put the copied value in all channels of the destination"
    )

  @classmethod
  def poll(cls, context):
    active_obj = context.active_object
    return active_obj != None and active_obj.type == 'MESH'

  def execute(self, context):
    src_id = context.scene.src_vcol_id
    dst_id = context.scene.dst_vcol_id
    src_channel_idx = channel_id_to_idx(context.scene.src_channel_id)
    dst_channel_idx = channel_id_to_idx(context.scene.dst_channel_id)
    mesh = context.active_object.data

    copy_channel(mesh, src_id, dst_id, src_channel_idx, dst_channel_idx, self.swap_channels, self.all_channels)

    return {'FINISHED'}


class VertexColorMaster_BlendChannels(bpy.types.Operator):
  """Blend source and destination channels (result is saved in destination)"""
  bl_idname = 'vertexcolormaster.blend_channels'
  bl_label = 'VCM Blend Channels'
  bl_options = {'REGISTER', 'UNDO'}

  blend_mode = bpy.props.EnumProperty(
    name = "blend mode",
    items=channel_blend_mode_items,
    description="Blending operation",
    default='ADD'
    )

  result_channel_id = EnumProperty(
    name="Result Channel",
    items=channel_items,
    description="Use this channel instead of destination"
    )

  @classmethod
  def poll(cls, context):
    active_obj = context.active_object
    return active_obj != None and active_obj.type == 'MESH'

  def invoke(self, context, event):
    self.result_channel = context.scene.dst_channel_id
    return self.execute(context)

  def execute(self, context):
    src_id = context.scene.src_vcol_id
    dst_id = context.scene.dst_vcol_id
    src_channel_idx = channel_id_to_idx(context.scene.src_channel_id)
    dst_channel_idx = channel_id_to_idx(context.scene.dst_channel_id)
    result_channel_idx = channel_id_to_idx(self.result_channel_id)
    mesh = context.active_object.data

    blend_channels(mesh, src_id, dst_id, src_channel_idx, dst_channel_idx, result_channel_idx, self.mode)

    return {'FINISHED'}
  


class VertexColorMaster_Fill(bpy.types.Operator):
  """Fill the active vertex color channel(s)"""
  bl_idname = 'vertexcolormaster.fill'
  bl_label = 'VCM Fill'
  bl_options = {'REGISTER', 'UNDO'}

  value = bpy.props.FloatProperty(
    name = "value",
    default = 1.0,
    min = 0.0,
    max = 1.0,
    description = "Value to fill channel(s) with"
    )

  clear_inactive = bpy.props.BoolProperty(
    name = "clear inactive",
    default = False,
    description = "Clear inactive channel(s)"
    )

  @classmethod
  def poll(cls, context):
    active_obj = context.active_object
    return active_obj != None and active_obj.type == 'MESH'

  def execute(self, context):
    active_channels = context.scene.active_channels
    mesh = context.active_object.data

    if mesh.vertex_colors:
      vcol_layer = mesh.vertex_colors.active
    else:
      vcol_layer = mesh.vertex_colors.new()

    value = self.value
    rmul = 1.0 if not self.clear_inactive or red_id in active_channels else 0.0
    gmul = 1.0 if not self.clear_inactive or green_id in active_channels else 0.0
    bmul = 1.0 if not self.clear_inactive or blue_id in active_channels else 0.0

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
    active_obj = context.active_object
    return active_obj != None and active_obj.type == 'MESH'

  def execute(self, context):
    active_channels = context.scene.active_channels
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
    name = "steps",
    default = 2,
    min = 2,
    max = 256,
    description = "Number of different grayscale values for posterization"
    )

  @classmethod
  def poll(cls, context):
    active_obj = context.active_object
    return active_obj != None and active_obj.type == 'MESH'

  def execute(self, context):
    active_channels = context.scene.active_channels
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
    name='blend mode',
    default='MIX',
    items=brush_blend_mode_items
    )

  @classmethod
  def poll(cls, context):
    active_obj = context.active_object
    return active_obj != None and active_obj.type == 'MESH'

  def execute(self, context):
    brush = bpy.data.brushes['Draw']
    brush.vertex_tool = self.blend_mode

    return {'FINISHED'}



##### MAIN CLASS, UI AND REGISTRATION #####
class VertexColorMaster(bpy.types.Panel):
  """COMMENT"""
  bl_space_type = 'VIEW_3D'
  bl_region_type = 'TOOLS'
  bl_label = 'Vertex Color Master'
  bl_category = 'Tools'
  bl_context = 'vertexpaint'

  def update_rgba(self, context):
    active_channels = context.scene.active_channels
    brush_value = context.scene.brush_value

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

  bpy.types.Scene.active_channels = EnumProperty(
    name="Active Channels",
    options={'ENUM_FLAG'},
    items=channel_items,
    description="Which channels to enable",
    default={'R', 'G', 'B'},
    update=update_rgba,
    )

  bpy.types.Scene.brush_value = FloatProperty(
    name="Brush Value",
    description="Value of the brush color",
    default=1.0,
    min=0.0,
    max=1.0,
    update=update_rgba,
    )

  def vcol_layer_items(self, context):
    obj = context.active_object
    mesh = context.active_object.data
    vertex_colors = [] if mesh.vertex_colors is None else [(vcol.name, vcol.name, '') for vcol in mesh.vertex_colors]
    vertex_groups = [(group.name, 'W: ' + group.name, '') for group in obj.vertex_groups]
    vertex_colors.extend(vertex_groups)

    return vertex_colors

  bpy.types.Scene.src_vcol_id = EnumProperty(
    name="Source Layer",
    items=vcol_layer_items,
    description="Source vertex color layer",
    )

  bpy.types.Scene.src_channel_id = EnumProperty(
    name="Source Channel",
    items=channel_items,
    description="Source color channel"
    )

  bpy.types.Scene.dst_vcol_id = EnumProperty(
    name="Destination Layer",
    items=vcol_layer_items,
    description="Destination vertex color layer",
    )

  bpy.types.Scene.dst_channel_id = EnumProperty(
    name="Destination Channel",
    items=channel_items,
    description="Destination color channel"
    )

  bpy.types.Scene.channel_blend_mode = bpy.props.EnumProperty(
    name = "Channel Blend Mode",
    items=channel_blend_mode_items,
    description="Channel blending operation",
    )

  def draw(self, context):
    layout = self.layout
    scn = context.scene
    obj = context.active_object

    # Brush Settings
    brush = bpy.data.brushes['Draw']
    col = layout.column(align=True)
    row = col.row()
    row.label('Brush Settings')
    row = col.row(align=True)
    row.prop(brush, 'color', text = "")
    row.prop(scn, 'brush_value', 'Val', slider=True)

    col = layout.column(align=True)
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
    row.operator('vertexcolormaster.edit_brush_settings', "Multiply").blend_mode = 'MUL'
    row.operator('vertexcolormaster.edit_brush_settings', "Lighten").blend_mode = 'LIGHTEN'
    row.operator('vertexcolormaster.edit_brush_settings', "Darken").blend_mode = 'DARKEN'

    layout.separator()

    # Active Channel Operations
    col = layout.column(align=True)
    row = col.row()
    row.label('Active Channels')
    row = col.row()
    row.prop(scn, 'active_channels', expand=True)

    col = layout.column(align=True)
    row = col.row(align = True)
    row.operator('vertexcolormaster.fill', 'Fill').value = 1.0
    row.operator('vertexcolormaster.fill', 'Clear').value = 0.0
    row = col.row(align = True)
    row.operator('vertexcolormaster.invert', 'Invert')
    row.operator('vertexcolormaster.posterize', 'Posterize')

    layout.separator()

    # Source->Destination Channel Operations
    col = layout.column(align=True)
    row = col.row()
    row.label('Channel/Weights Transfer')
    src_is_vg = scn.src_vcol_id in obj.vertex_groups
    dst_is_vg = scn.dst_vcol_id in obj.vertex_groups

    lcol_percentage = 0.8
    row = layout.row()
    split = row.split(lcol_percentage, align=True)
    col = split.column(align=True)
    col.prop(scn, 'src_vcol_id', 'Src')
    split = split.split(align=True)
    col = split.column(align=True)
    col.prop(scn, 'src_channel_id', '')
    col.enabled = not src_is_vg

    row = layout.row()
    split = row.split(lcol_percentage, align=True)
    col = split.column(align=True)
    col.prop(scn, 'dst_vcol_id', 'Dst')
    split = split.split(align=True)
    col = split.column(align=True)
    col.prop(scn, 'dst_channel_id', '')
    col.enabled = not dst_is_vg

    if not (src_is_vg or dst_is_vg):
      row = layout.row(align=True)
      row.operator('vertexcolormaster.copy_channel', 'Copy').swap_channels = False
      row.operator('vertexcolormaster.copy_channel', 'Swap').swap_channels = True

      col = layout.column(align=True)
      row = col.row()
      row.operator('vertexcolormaster.blend_channels', 'Blend').blend_mode = scn.channel_blend_mode
      row.prop(scn, 'channel_blend_mode', '')

      col = layout.column(align=True)
      row = col.row(align=True)
      row.operator('vertexcolormaster.rgb_to_grayscale', 'Src RGB to luminosity')
      row = col.row(align=True)
      row.operator('vertexcolormaster.copy_channel', 'Src ({0}) to Dst RGB'.format(scn.src_channel_id)).all_channels = True
    elif src_is_vg and not dst_is_vg:
      row = layout.row(align=True)
      row.operator('vertexcolormaster.weights_to_color', 'Weights to Dst ({0})'.format(scn.src_channel_id))
    elif dst_is_vg and not src_is_vg:
      row = layout.row(align=True)
      row.operator('vertexcolormaster.color_to_weights', 'Src ({0}) to Weights'.format(scn.src_channel_id))
    # else: # src_is_vg and dst_is_vg
      # row = layout.row(align=True)
      # row.operator('vertexcolormaster.copy_channel', 'Copy')
      # row.operator('vertexcolormaster.copy_channel', 'Swap')

    # scale val to range

    # manage vertex color layers (copy ui from obj data?)


##### OPERATOR REGISTRATION #####
def register():
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