# Vertex Color Master for Blender
An add-on for Blender that adds numerous features to assist working with vertex colors.

## Installation
1. Download the script from GitHub by clicking [here](https://github.com/andyp123/blender_vertex_color_master/archive/master.zip).
2. Open the downloaded .zip and extract the file 'vertex_color_master.py' to a temporary place on your computer.
3. In Blender, open the User Preferences (ctrl+alt+p) and switch to the Add-ons tab.
4. Select 'Install Add-on from file...' and select the 'vertex_color_master.py' file you extracted from the .zip.
5. Search for the add-on in the list (enter 'vertex' to quickly find it) and enable it.
6. Save the user settings if you would like the script to always be enabled.

__Note:__ If you are using a 2.79 based Buildbot version of Blender (available [here](https://builder.blender.org/download/)), you may use vertex color alpha, which must be enabled in the add-on preferences. To do this, click on the small arrow to the left of the add-on name in the Add-ons tab and under Preferences enable 'Alpha Support'. If you don't have a compatible version of Blender, enabling alpha support will result in errors.

## Usage
This add-on is mostly designed for people who use vertex colors as extra non-color data, such as artists making models for games, where such data can be useful for creating interesting shader effects, or for storing baked light data. The tools provided by this add-on allow the user to fill, invert or posterize individual color channels, as well as copy or swap channels between layers and exchange vertex weight data to and from color channels.

The add-on will appear in the Brush tab of the tools menu in vertex paint mode as shown in the following image.

![Vertex Color Master UI](https://raw.githubusercontent.com/andyp123/blender_vertex_color_master/master/README_img/vertex_color_master.png)

## Functions

### Brush Settings
Brush settings contains a few of the most useful brush options so that the add-on can be open and useful without needing the full brush menu to be open. This way there is more space in the Tools panel, even on smaller displays.

+ __Match Active Channels__ (on) - With this option enabled, changing the active channels will update the brush color to match the channels that are active, such that enabling only R will give red, R and G will give yellow and all RGB will give white etc. If this is undesirable, disable this option.

### Active Channels
The active channels section allows the user to enable or disable channels that the functions directly under the active channels will work on. For example, enabling only the R channel will mean that it is the only channel to be affected when the Invert button is pressed, etc. Different combinations of RGBA can be selected by holding the shift key while clicking on the channel buttons.

As channels are activated and deactivated, the brush color will update to match them. If the Add or Subtract brush blending modes are set, this enables the user to paint only on active channels quite easily.

### Fill / Clear
Fill sets the value of the currently active channel(s) to 1, whereas Clear will set it to 0.

+ __Value__ (1.0) - The value to fill the channel(s) with.

+ __Clear Inactive__ (off) - Clear channels that are not activated in the Active Channels settings.

+ __Clear Alpha__ (off) - Even if clear inactive is enabled, if this setting is off, the alpha channel will not be cleared when using Fill. __Note:__ Only available when Alpha Support is enabled in the add-on preferences.

### Invert
Inverts the value of the currently active channel(s).

### Posterize
Posterize the value of the currently active channel(s). Useful for cleaning up channels where the value should be 0 or 1, or otherwise snapping the value to increments determined by the number of steps.

+ __Steps__ (2) - The number of value steps to posterize to. For example, setting this to 5 would snap the values of the active channel(s) to 0, 0.25, 0.5, 0.75 and 1, whilst leaving the default setting of 2, would result in black and white.

### Channel/Weights Transfer
This section allows quick transfer of data between different vertex color and vertex groups on the same object. Values can be transferred between 'Src' and 'Dst' layers. When using a vertex color layer, the RGBA channel will be selectable from the channel dropdown on the right. If a vertex group is selected (vertex groups are prefixed with 'W:', for weight), the channel dropdown will be disabled.

If a vertex group is selected in either 'Src' or 'Dst', a different UI will be shown that enables only weight transfer. Transfer between two vertex groups is currently unsupported.

### Copy / Swap
Copy data from the 'Src' layer/channel to the 'Dst' layer/channel. Using swap will swap the data instead of copy.

+ __Swap Channels__ (off) - Swap 'Src' and 'Dst'  channel data instead of just copying from 'Src' to 'Dst'.

+ __All Channels__ (off) - If swap is disabled, the data from the 'Src' channel will be copied to all channels of the 'Dst' layer.

### Blend
Blends the 'Src' channel with the 'Dst' channel and puts the result in the 'Dst' channel by default.

+ __Blend Mode__ (Add) - Set the blending mode to use.

+ __Result Channel__ (R) - Set a different channel to put the resulting data of the blend if overwriting the 'Dst' channel is not desired.

### Src RGB to Luminosity
This calculates the luminosity of the vertex color data in the 'Src' layer and puts the value into each of the RGB channels.

+ __All Channels__ (on) - Copy the luminosity value into each of the RGB channels. If disabled, theh luminosity value will only be copied into the 'Dst' layer's selected channel.

### Src to Dst RGB
Copy the value of the 'Src' channel into all channels of the 'Dst' layer.

### Weights to Dst
Copy the weight value of the vertex group in the 'Src' layer to the 'Dst' channel.

### Src to Weights
Copy the value of the 'Src' channel to the vertex group in the 'Dst' layer.

## Planned Features
* Active Channel functions selection only option to operate just on selected elements (vertex, face).
* Channel isolation mode for painting grayscale and saving to a channel more easily.
* Improve alpha support:
  - Auto detect support instead of enabling it in preferences.
  - Enable RGB channels in Active Channels by default.
* Add more operator inputs to the Redo panel.