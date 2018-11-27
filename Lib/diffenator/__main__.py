# Copyright 2017 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Font Diffenator
~~~~~~~~~~~~~~~

Report differences between two fonts.

Diffs can be made for the following categories, names, marks, mkmks,
attribs, metrics, glyphs and kerns.

Examples
--------
Diff everything:
diffenator /path/to/font_a.ttf /path/to/font_b.ttf

Diff just a nametable:
diffenator /path/to/font_a.ttf /path/to/font_b.ttf -td names

Diff nametable and marks:
diffenator /path/to/font_a.ttf /path/to/font_b.ttf -td names marks

Output report as markdown:
diffenator /path/to/font_a.ttf /path/to/font_b.ttf -md

Diff kerning and ignore differences under 30 units:
diffenator /path/to/font_a.ttf /path/to/font_b.ttf -td kerns --kerns_thresh 30

Output images:
diffenator /path/to/font_a.ttf /path/to/font_b.ttf -r /path/to/img_dir
"""
from argparse import RawTextHelpFormatter
from diffenator import CHOICES, __version__
from diffenator.font import DFont
from diffenator.diff import DiffFonts
import argparse


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=RawTextHelpFormatter)
    parser.add_argument('--version', action='version', version=__version__)

    parser.add_argument('font_a')
    parser.add_argument('font_b')
    parser.add_argument('-td', '--to_diff', nargs='+', choices=CHOICES,
                        default='*',
                        help="categories to diff. '*'' diffs everything")

    parser.add_argument('-ol', '--output-lines', type=int, default=50,
                        help="Amout of diffs to report for each diff table")
    parser.add_argument('-md', '--markdown', action='store_true',
                        help="Output report as markdown.")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Report diffs which are the same')

    parser.add_argument('-i', '--vf-instance', default='wght=400',
                        help='Set vf variations e.g "wght=400"')

    parser.add_argument('--marks_thresh', type=int, default=0,
                        help="Ignore modified marks under this value")
    parser.add_argument('--mkmks_thresh', type=int, default=0,
                        help="Ignore modified mkmks under this value")
    parser.add_argument('--kerns_thresh', type=int, default=0,
                        help="Ignore modified kerns under this value")
    parser.add_argument('--glyphs_thresh', type=float, default=0,
                        help="Ignore modified glyphs under this value")
    parser.add_argument('--metrics_thresh', type=int, default=0,
                        help="Ignore modified metrics under this value")
    parser.add_argument('-rd', '--render_diffs', action='store_true',
                        help=("Render glyphs with hb-view and compare "
                              "pixel diffs."))
    parser.add_argument('-r', '--render-path',
                        help="Path to generate before and after gifs to.")
    args = parser.parse_args()

    diff_options = dict(
            marks_thresh=args.marks_thresh,
            mkmks_thresh=args.mkmks_thresh,
            kerns_thresh=args.kerns_thresh,
            glyphs_thresh=args.glyphs_thresh,
            metrics_thresh=args.metrics_thresh,
            to_diff=set(args.to_diff),
    )
    font_a = DFont(args.font_a)
    font_b = DFont(args.font_b)

    if font_a.is_variable and not font_b.is_variable:
        font_a.set_variations_from_static(font_b)

    elif not font_a.is_variable and font_b.is_variable:
        font_b.set_variations_from_static(font_a)

    elif font_a.is_variable and font_b.is_variable:
        variations = {s.split('=')[0]: float(s.split('=')[1]) for s
                      in args.vf_instance.split(", ")}
        font_a.set_variations(variations)
        font_b.set_variations(variations)

    diff = DiffFonts(font_a, font_b, diff_options)

    if args.markdown:
        print(diff.to_md(args.output_lines))
    else:
        print(diff.to_txt(args.output_lines))

    if args.render_path:
        diff.to_gifs(args.render_path)


if __name__ == '__main__':
    main()

