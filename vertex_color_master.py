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


# + Transfer vertex colors to single channel 
# + paint greyscale, r, g, b or whatever
# + convert colors by luminosity, channel copy, channel mask, channel swap
# + fill channel with color
# + fill can use selection as a mask
# + fill can have fade out from selection (i.e. selected verts are 1.0, verts at fade dist are 0, and in between are lerped)
# + support alpha using technique from existing vcolor addons
# + convert vcol to weights and back
# + convert weights to channel
# + channel viewer

# where is the vcol data stored? temp vcol channel, or temp object copy?
# blender only supports r,g,b. could use two rgb channels giving 6 channels total

# first steps
# fill channel
# invert channel
# use vertex selection mask with fill and invert
#   selection using vertices must get each vertex from loop data (per face vertex)
#   selection usin faces must get just the loop for entire face

# TODO:
# active channels is weird. Just make RGBA part of the brush settings and call it brush_channels or something
# think about workflow properly
#
#

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
  "description": "Tools to make working with vertex colors with greater precision than using the paint brush.",
  "category": "Paint"
}

red_id = 'R'
green_id = 'G'
blue_id = 'B'
alpha_id = 'A'


##### HELPER FUNCTIONS #####
def set_channels_visible(object, active_channels):
  return None

def set_brush_params(brush_opacity, brush_mode, active_channels):
  return None

##### MAIN OPERATOR CLASSES #####
class VertexColorMaster_Fill(bpy.types.Operator):
  """Fill the active vertex color channel with the current color"""
  bl_idname = 'vertexcolormaster.fill'
  bl_label = 'VCM Fill with color'
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

    fill_color = bpy.data.brushes['Draw'].color

    for loop_index, loop in enumerate(mesh.loops):
      vcol_layer.data[loop_index].color = fill_color

    mesh.vertex_colors.active = vcol_layer
    mesh.update()

    return {'FINISHED'}

class VertexColorMaster_Invert(bpy.types.Operator):
  """Invert active vertex color channel(s)"""
  bl_idname = 'vertexcolormaster.invert'
  bl_label = 'Invert vertex color channel(s)'
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
      # if alpha_id in active_channels:
      vcol_layer.data[loop_index].color = color

    mesh.vertex_colors.active = vcol_layer
    mesh.update()

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

    # update rgba of vertex colors shown in viewport to match mask
    return None

  channel_items = ((red_id, "R", ""), (green_id, "G", ""), (blue_id, "B", ""), (alpha_id, "A", ""))

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
    step=0.5,
    update=update_rgba,
    )

  def draw(self, context):
    layout = self.layout

    brush = bpy.data.brushes['Draw']
    col = layout.column(align=True)
    row = col.row()
    row.label('Brush Color')
    row = col.row()
    row.prop(brush, "color", text = "")
    row.prop(context.scene, "brush_value")

    col = layout.column(align=True)
    row = col.row()
    row.label('Active Channels')
    row = col.row()
    row.prop(context.scene, "active_channels", expand=True)

    layout.separator()
    row = layout.row()
    row.operator('vertexcolormaster.fill')
    row = layout.row()
    row.operator('vertexcolormaster.invert')



##### OPERATOR REGISTRATION #####
def register():
  bpy.utils.register_class(VertexColorMaster)
  bpy.utils.register_class(VertexColorMaster_Fill)
  bpy.utils.register_class(VertexColorMaster_Invert)


def unregister():
  bpy.utils.unregister_class(VertexColorMaster)
  bpy.utils.unregister_class(VertexColorMaster_Fill)
  bpy.utils.unregister_class(VertexColorMaster_Invert)


# allows running addon from text editor
if __name__ == '__main__':
  register()