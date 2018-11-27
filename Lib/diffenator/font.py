"""DFont inherits TTFont and adds an input map attribute. This attrib
contains a glyph object which contains the input, features for each glyph.
"""
from fontTools.misc.py23 import unichr
from fontTools.ttLib import TTFont
from fontTools.varLib.mutator import instantiateVariableFont
from diffenator.hbinput import HbInputGenerator
from diffenator.dump import (
        DumpAnchors,
        dump_kerning,
        dump_glyphs,
        dump_glyph_metrics,
        dump_attribs,
        dump_nametable
)
import sys
try:
    # try and import unicodedata2 backport for py2.7.
    import unicodedata2 as uni
except ImportError:
    # on py2.7, this module only goes up to unicode 5.2.0 so it won't support
    # recently added glyphs.
    import unicodedata as uni
if sys.version_info.major == 3:
    unicode = str


class DFont(TTFont):
    """Wrapper for TTFont object which contains an input map to generate
    a glyph. This object will be deprecated once otLib progresses"""
    def __init__(self, file=None, lazy=False):
        self._ttfont = TTFont(file)
        self._glyphset = self._gen_inputs() if file else []
        self._axis_locations = None
        self._axis_order = None
        self._path = file
        self._src = self._ttfont
        self._glyphs = self._marks = self._mkmks = self._kerns = \
            self._glyph_metrics = self._names = self._attribs = None

        if not lazy:
            self.recalc_tables()

    @property
    def path(self):
        return self._path

    @property
    def glyphset(self):
        return self._glyphset

    def glyph(self, name):
        return self._glyphset[name]

    @property
    def axis_order(self):
        return self._axis_order

    @property
    def axis_locations(self):
        return self._axis_locations

    def _gen_inputs(self):
        if not 'cmap' in self._ttfont.keys():
            return []
        inputs = InputGenerator(self._ttfont).all_inputs()
        return {g.name: g for g in inputs}

    def recalc_input_map(self):
        self._input_map = self._gen_inputs()

    @property
    def is_variable(self):
        if 'fvar' in self._src:
            return True
        return False

    def set_variations(self, axes):
        """Instantiate a ttfont VF with axes vals"""
        if self.is_variable:
            self._ttfont = instantiateVariableFont(self._src, axes, inplace=False)
            self._axis_order = [a.axisTag for a in self._src['fvar'].axes]
            self._axis_locations = {a.axisTag: a.defaultValue for a in
                                    self._src['fvar'].axes}
            for axis in axes:
                if axis in self._axis_locations:
                    self._axis_locations[axis] = axes[axis]
                else:
                    print("font has no axis called {}".format(axis))
            self.recalc_tables()
        else:
            print("Not vf")

    def set_variations_from_static(self, dfont):
        """Set the variations of a variable font using the vals from a
        static font"""
        variations = {}
        if self.is_variable:
            variations["wght"] = dfont._ttfont["OS/2"].usWeightClass
            # TODO (M Foley) add wdth, slnt axes
            self.set_variations(variations)

    def recalc_tables(self):
        """Recalculate DFont tables"""
        anchors = DumpAnchors(self)
        self._glyphs = dump_glyphs(self)
        self._marks = anchors.marks_table
        self._mkmks = anchors.mkmks_table
        self._glyph_metrics = dump_glyph_metrics(self)
        self._attribs = dump_attribs(self)
        self._names = dump_nametable(self)
        self._kerns = dump_kerning(self)
        self._metrics = dump_glyph_metrics(self)

    @property
    def glyphs(self):
        return self._glyphs

    @property
    def marks(self):
        return self._marks

    @property
    def mkmks(self):
        return self._mkmks

    @property
    def glyph_metrics(self):
        return self._glyph_metrics

    @property
    def attribs(self):
        return self._attribs

    @property
    def names(self):
        return self._names

    @property
    def kerns(self):
        return self._kerns

    @property
    def metrics(self):
        return self._metrics


class InputGenerator(HbInputGenerator):
    """Taken from Nototool's HbIntputGenerator"""

    def all_inputs(self, warn=False):
        """Generate harfbuzz inputs for all glyphs in a given font."""

        inputs = []
        glyph_set = self.font.getGlyphSet()
        for name in self.font.getGlyphOrder():
            is_zero_width = glyph_set[name].width == 0
            cur_input = self.input_from_name(name, pad=is_zero_width)
            if cur_input is not None:
                features, characters = cur_input
                characters = characters.replace(' ', '')
                inputs.append(
                    Glyph(name, features, unicode(characters), self.font)
                )
            else:
                features = ('',)
                inputs.append(Glyph(name, features, '', self.font))
        return inputs

    def input_from_name(self, name, seen=None, pad=False):
        """Given glyph name, return input to harbuzz to render this glyph.

        Returns input in the form of a (features, text) tuple, where `features`
        is a list of feature tags to activate and `text` is an input string.

        Argument `seen` is used by the method to avoid following cycles when
        recursively looking for possible input. `pad` can be used to add
        whitespace to text output, for non-spacing glyphs.

        Can return None in two situations: if no possible input is found (no
        simple unicode mapping or substitution rule exists to generate the
        glyph), or if the requested glyph already exists in `seen` (in which
        case this path of generating input should not be followed further).
        """

        if name in self.memo:
            return self.memo[name]

        inputs = []

        # avoid following cyclic paths through features
        if seen is None:
            seen = set()
        if name in seen:
            return None
        seen.add(name)

        # see if this glyph has a simple unicode mapping
        if name in self.reverse_cmap:
            text = unichr(self.reverse_cmap[name])
            if text != unichr(0):
                inputs.append(((), text))

        # check the substitution features
        inputs.extend(self._inputs_from_gsub(name, seen))
        # seen.remove(name)

        # since this method sometimes returns None to avoid cycles, the
        # recursive calls that it makes might have themselves returned None,
        # but we should avoid returning None here if there are other options
        inputs = [i for i in inputs if i is not None]
        if not inputs:
            return None

        features, text = min(inputs)
        # can't pad if we don't support space
        if pad and self.space_width > 0:
            width, space = self.widths[name], self.space_width
            padding = ' ' * (width // space + (1 if width % space else 0))
            text = padding + text
        self.memo[name] = features, text
        return self.memo[name]


class Glyph:
    def __init__(self, name, features, characters, font):
        self.name = name
        self.features = features
        self.characters = characters
        self.combining = True if characters and uni.combining(characters[0]) else False
        self.key = self.characters + ''.join(features)
        self.font = font

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name
