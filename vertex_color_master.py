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


import bpy


bl_info = {
  "name": "Vertex Color Master",
  "author": "Andrew Palmer",
  "version": (0, 0, 1),
  "blender": (2, 79, 0),
  "location": "",
  "description": "Tools to make working with vertex colors with greater precision than using the paint brush.",
  "category": "Paint"
}


rgb_channel_id = 'VCM_rgb'
alpha_channel_id = 'VCM_a'
channel_r = 1
channel_g = 2
channel_b = 4
channel_a = 8
channel_mask = 15;


##### HELPER FUNCTIONS #####

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
    active_obj = context.active_object
    mesh = active_obj.data

    if mesh.vertex_colors:
      vcol_layer = mesh.vertex_colors.active
    else:
      vcol_layer = mesh.vertex_colors.new()

    draw_color = bpy.data.brushes['Draw'].color

    for loop_index, loop in enumerate(mesh.loops):
      color = vcol_layer.data[loop_index].color
      if channel_mask & channel_r:
        color[0] = draw_color[0]
      if channel_mask & channel_g:
        color[1] = draw_color[1]
      if channel_mask & channel_b:
        color[2] = draw_color[2]
      # if channel_mask & channel_a:
      vcol_layer.data[loop_index].color = color

    mesh.vertex_colors.active = vcol_layer

    mesh.update()


    return {'FINISHED'}


##### MAIN CLASS, UI AND REGISTRATION #####
class VertexColorMaster_UI(bpy.types.Panel):
  """COMMENT"""
  bl_space_type = 'VIEW_3D'
  bl_region_type = 'TOOLS'
  bl_label = 'Vertex Color Master'
  bl_category = 'Tools'
  bl_context = 'vertexpaint'

  def draw(self, context):
    layout = self.layout

    # col = layout.column()
    # col.label("Hello!")
    row = layout.row()
    row.operator('vertexcolormaster.fill')


##### OPERATOR REGISTRATION #####
def register():
  bpy.utils.register_class(VertexColorMaster_UI)
  bpy.utils.register_class(VertexColorMaster_Fill)


def unregister():
  bpy.utils.unregister_class(VertexColorMaster_UI)
  bpy.utils.unregister_class(VertexColorMaster_Fill)


# allows running addon from text editor
if __name__ == '__main__':
  register()