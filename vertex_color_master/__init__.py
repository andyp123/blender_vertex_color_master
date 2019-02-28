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

# reload submodules if the addon is reloaded 
if "bpy" in locals():
    import importlib
    importlib.reload(vcm_globals)
    importlib.reload(vcm_main)
    importlib.reload(vcm_menus)
    importlib.reload(vcm_ops)
    importlib.reload(vcm_helpers)

import bpy
from . import vcm_main
from . import vcm_menus
from . import vcm_ops
# not used in this file
from . import vcm_globals
from . import vcm_helpers

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
    vcm_ops.VERTEXCOLORMASTER_OT_Gradient,
    vcm_menus.VERTEXCOLORMASTER_PT_MainPanel,
    vcm_menus.VERTEXCOLORMASTER_MT_PieMain,
)

# used to unregister bound shortcuts when the addon is disabled / removed
addon_shortcuts = []

def register():
    # add operators
    for c in classes:
        bpy.utils.register_class(c)

    # register properties (see also VertexColorMasterProperties class)
    bpy.types.Scene.vertex_color_master_settings = bpy.props.PointerProperty(
        type=vcm_main.VertexColorMasterProperties)

    # register shortcuts
    wm = bpy.context.window_manager
    if wm.keyconfigs.addon:
        km = wm.keyconfigs.addon.keymaps.new(name='Vertex Paint')
        kmi = km.keymap_items.new('wm.call_menu_pie', 'V', 'PRESS')
        kmi.properties.name = "vertexcolormaster.pie_main"
        kmi.active = True
        addon_keymaps.append((km, kmi))  

def unregister():
    # remove operators
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

    # unregister properties
    del bpy.types.Scene.vertex_color_master_settings

    # unregister shortcuts
    wm = bpy.context.window_manager
    if wm.keyconfigs.addon:
        for km in addon_keymaps:
            for kmi in km.keymap_items:
                km.keymap_items.remove(kmi)

            wm.keyconfigs.addon.keymaps.remove(km)

    del addon_keymaps[:]

# allows running addon from text editor
if __name__ == '__main__':
    register()