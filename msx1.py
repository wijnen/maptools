# Helpers for getting and presenting data from MSX1 ROM cartridges
# vim: set foldmethod=marker :

from PIL import Image
import svgmap
import struct

rom = open('nemesis.rom', 'rb').read()

def addr2rom(address, page): # {{{
	'Convert address and page to an address in the rom file. page may be any of the 3 pages (so 6000,4 is the same as 6000,5)'
	if page is None:
		return address
	if page == 0:
		base = address - 0x4000
		firstpage = 0
	else:
		base = address - 0x6000 # address from start of (changed) mappings.
		firstpage = ((page - 1) // 3) * 3 + 1   # First page of the set of 3.
	return base + firstpage * 0x2000
# }}}

def read_word(addr, page): # {{{
	romaddr = addr2rom(addr, page)
	word = struct.unpack('<H', rom[romaddr:romaddr + 2])[0]
	return word
# }}}

# This palette is hardcoded into the MSX1 VDP.
# Color 0 should be transparent, but PIL is not working as documented.
msx1_palette = ((0, 0, 0, # {{{
                0, 0, 0,
                62, 184, 73,
                116, 208, 125,
                89, 85, 224,
                128, 118, 241,
                185, 94, 81,
                101, 219, 239,
                219, 101, 89,
                255, 137, 125,
                204, 195, 94,
                222, 208, 135,
                58, 162, 65,
                183, 102, 181,
                204, 204, 204,
                255, 255, 255))
# }}}

def mkchar(pgt, ct): # {{{
	'Create an image from screen 2 data. Both arguments must be 8-sequences. The returned image is mode PA with the default palette.'
	assert len(pgt) == 8 and len(ct) == 8
	ret = Image.new('P', (8, 8))
	ret.putpalette(msx1_palette)
	for y, pc in enumerate(zip(pgt, ct)):
		p, c = pc
		colors = (c & 0xf, (c >> 4) & 0xf)
		for pixel in range(8):
			state = (p >> (7 - pixel)) & 1
			ret.putpixel((pixel, y), colors[state])
	return ret
# }}}

def toRGBA(char): # {{{
	'Convert a character (or any other mode P image) into RGBA using color 0 as transparent'
	ret = char.convert('RGBA')
	alpha = char.copy()
	alpha.putpalette((0, 0, 0) + (255, 255, 255) * 15)
	ret.putalpha(alpha.convert('1'))
	return ret
# }}}

def svg(): # {{{
	'Create a new svg document with sane settings (pixelated images).'
	return svgmap.svg(style = {'image-rendering': 'pixelated'})
# }}}
