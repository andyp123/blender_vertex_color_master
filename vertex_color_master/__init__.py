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
from . import vcm_main
from . import vcm_ops

bl_info = {
    "name": "Vertex Color Master",
    "author": "Andrew Palmer (with contributions from Bartosz Styperek)",
    "version": (0, 80),
    "blender": (2, 80, 0),
    "location": "Vertex Paint | View3D > Vertex Color Master",
    "description": "Tools for manipulating vertex color data.",
    "warning": "",
    "wiki_url": "https://github.com/andyp123/blender_vertex_color_master",
    "tracker_url": "https://github.com/andyp123/blender_vertex_color_master/issues",
    "category": "Paint",
}

classes = (
    vcm_main.VertexColorMasterProperties,
    vcm_main.VERTEXCOLORMASTER_PT_MainPanel,
    vcm_ops.VERTEXCOLORMASTER_OT_QuickFill,
    vcm_ops.VERTEXCOLORMASTER_OT_Fill,
    vcm_ops.VERTEXCOLORMASTER_OT_Invert,
    vcm_ops.VERTEXCOLORMASTER_OT_Posterize,
    vcm_ops.VERTEXCOLORMASTER_OT_Remap,
    vcm_ops.VERTEXCOLORMASTER_OT_CopyChannel,
    vcm_ops.VERTEXCOLORMASTER_OT_RgbToGrayscale,
    vcm_ops.VERTEXCOLORMASTER_OT_BlendChannels,
    vcm_ops.VERTEXCOLORMASTER_OT_EditBrushSettings,
    vcm_ops.VERTEXCOLORMASTER_OT_WeightsToColor,
    vcm_ops.VERTEXCOLORMASTER_OT_ColorToWeights,
    vcm_ops.VERTEXCOLORMASTER_OT_UVsToColor,
    vcm_ops.VERTEXCOLORMASTER_OT_ColorToUVs,
    vcm_ops.VERTEXCOLORMASTER_OT_IsolateChannel,
    vcm_ops.VERTEXCOLORMASTER_OT_ApplyIsolatedChannel,
    vcm_ops.VERTEXCOLORMASTER_OT_RandomizeMeshIslandColors,
    vcm_ops.VERTEXCOLORMASTER_OT_AdjustHSV,
    vcm_ops.VERTEXCOLORMASTER_OT_FlipBrushColors,
    vcm_ops.VERTEXCOLORMASTER_OT_LinearGradient,
)

def register():
    # add operators
    for c in classes:
        bpy.utils.register_class(c)

    # register properties (see also VertexColorMasterProperties class)
    bpy.types.Scene.vertex_color_master_settings = bpy.props.PointerProperty(
        type=vcm_main.VertexColorMasterProperties)

def unregister():
    # remove operators
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

    # unregister properties
    del bpy.types.Scene.vertex_color_master_settings

# allows running addon from text editor
if __name__ == '__main__':
    register()