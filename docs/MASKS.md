# Masks and effects

Select a video clip and open Clip video effects. Color and effects contains the existing
adjustments plus sepia, mirror, pixelation, sharpen and vignette.

On Mask and preview, select rectangle/ellipse and drag, select polygon and click vertices,
or select freehand and drag a closed outline. Start new drawing clears the pending polygon
vertices; selecting none disables masking. Position and size fields transform the shape in
normalized canvas coordinates. Invert applies blur outside. Feather softens the boundary;
strength blends the blurred and original frames. Blur and feather are project-width pixels.
One static mask per clip is supported, with up to 256 vertices; no tracking or keyframes.

Render effects preview produces a background still at the selected clip-frame offset,
using the export graph and a maximum 640 by 360 proxy. Four results are cached per dialog.
Render again after changes; the Timeline monitor remains untreated. Preview jobs have a
30-second timeout; closing waits for the active job to finish. Preview excludes other clips,
audio and subtitles. Export uses full chosen resolution. OK commits one undoable edit;
Cancel discards drafts. Project schema 6 persists masks and reads schemas 1 through 6.
