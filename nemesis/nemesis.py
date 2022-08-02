#!/usr/bin/python3

from msx1 import *
from PIL import ImageOps
from svgmap import *
import numpy as np

twinbee = False

# Characters {{{
def read_raw_chars(start_addr, page, num):
	'''This code is used for reading the font, which is stored without compression.'''
	ret = []
	for n in range(num):
		ret.append([])
		for line in range(8):
			data = rom[addr2rom(start_addr + n * 8 + line, page)]
			ret[-1].append('{:08b}'.format(data).replace('0', ' ').replace('1', '#'))
	return ret

def show_font():
	for addr, num in ((0x5906, 0xd), (0x596e, 0x1b)):
		print('\n===\n'.join('\n'.join(x for x in char) for char in read_chars(addr, 0, num)))

def read_and_decode_character_data(addr, page, first):
	current = first
	ret = {current: b''}
	while True:
		data = rom[addr2rom(addr, page)]
		addr += 1
		if data == 0:
			break
		if (data & 0x80) == 0:
			b = rom[addr2rom(addr, page)]
			addr += 1
			ret[current] += bytes((b,)) * data
			continue
		if (data & 0x7f) == 0:
			target = read_word(addr, page)
			addr += 2
			print('new target location: %04x' % target)
			if len(ret[current]) == 0:
				del ret[current]
			current = target
			if target in ret:
				print('replacing %04x' % target)
			ret[current] = b''
			continue
		data &= 0x7f
		src = addr2rom(addr, page)
		ret[current] += rom[src:src + data]
		addr += data
	return ret

debugindex = 0
def read_characters(addr, page, datapage):
	global debugindex
	ret = [{}, {}, {}]
	debugimgs = []
	debugrow = 0
	while True:
		debugimgs.append(Image.new('RGB', (0x900, 8)))
		record = addr2rom(addr, page)
		if rom[record] == 0:
			break
		regions = set()
		for bit in range(3):
			if rom[record] & (1 << bit):
				regions.add(bit)
		#print('regions %x -> %s' % (rom[record], regions))
		pgt = read_word(addr + 1, page)
		ct = read_word(addr + 4, page)
		firstchar = rom[record + 3]
		pgt_chars = read_and_decode_character_data(pgt, datapage, firstchar * 8 + 0x2000)
		ct_chars = read_and_decode_character_data(ct, datapage, firstchar * 8)
		assert set(x - 0x2000 for x in pgt_chars.keys()) == set(ct_chars.keys())
		assert len(pgt_chars) == 1	# Not required, but seems to always be the case.
		for first in pgt_chars:
			#print('loading characters: %x' % ((first - 0x2000) // 8), 'pgt', len(pgt_chars[first]) // 8, 'ct', len(ct_chars[first - 0x2000]) // 8)
			for c in range(len(pgt_chars[first]) // 8):
				target = (first - 0x2000) // 8 + c
				pgtdata = pgt_chars[first][c * 8:(c + 1) * 8]
				ctdata = ct_chars[first - 0x2000][c * 8:(c + 1) * 8]
				#hack
				if len(ctdata) < 8:
					ctdata += bytes((0xf1,)) * (8 - len(ctdata))
				char = toRGBA(mkchar(pgtdata, ctdata))
				for r in regions:
					if target in ret[r]:
						#print('Warning: overwriting character %x' % target, first, c)
						pass
					ret[r][target] = char.convert('RGB')
				debugimgs[-1].paste(char, (9 * target, 0))
			debugrow += 1
		addr += 6
	debugimg = Image.new('RGB', (0x900, 9 * len(debugimgs)))
	for i, img in enumerate(debugimgs):
		debugimg.paste(img, (0, 9 * i))
	debugimg.save('/tmp/nemesis-chars-debug-%x.png' % debugindex)
	debugindex += 1
	#keys = list(ret.keys())
	#keys.sort()
	#print('loaded characters:', ' '.join('%02x' % x for x in keys))
	return ret

levels = 12
def load_charmap(level, svg = None):
	# TODO: font
	chars = read_characters(0x932d, 5, 4)
	more = read_characters(read_word(0x92e3 + level * 2, 5), 5, 4)
	for r in range(3):
		chars[r].update(more[r])
	def handle_mirror(table, transform, chars, type):
		addr = addr2rom(table, 5)
		ret = []
		while True:
			src = rom[addr]
			if src == 0:
				break
			dst = rom[addr + 1]
			regions = rom[addr + 2]
			num = rom[addr + 3]
			if regions & 0x4:
				rsrc = 2
			elif regions & 0x2:
				rsrc = 1
			else:
				rsrc = 0
			bit2region = {1: (0,), 2: (1,), 3: (0, 1), 4: (2,), 5: (0, 2), 6: (1, 2), 7: (0, 1, 2)}
			rdst = bit2region[(regions >> 3) & 0x7]
			#print('%smirror char %x@%x to %x@%s + %x' % (type, src, rsrc, dst, rdst, num))
			ret.append((type, src, dst, num))
			for d in rdst:
				for i in range(num):
					if (dst + i) in chars[d]:
						#print('Warning: mirror overwrites %x' % (dst + i))
						pass
					if (src + i) not in chars[rsrc]:
						print('Warning: mirror source %x does not exist' % (src + i))
						chars[d][dst + i] = Image.new('RGB', (8, 8), (255, 0, 255))
					else:
						chars[d][dst + i] = transform(chars[rsrc][src + i])
			addr += 4
		return ret
	hmirror = read_word(0x92fb + level * 2, 5)
	vmirror = read_word(0x9313 + level * 2, 5)
	dbg = []
	dbg.extend(handle_mirror(hmirror, ImageOps.mirror, chars, 'h'))
	dbg.extend(handle_mirror(vmirror, ImageOps.flip, chars, 'v'))
	if svg is not None:
		for i, (t, src, dst, num) in enumerate(dbg):
			svg.add('%s+%x' % (t, num), (src * 8, (i + 1) * 8), {'font-size': 4})
			svg.add('dst', (dst * 8, (i + 1) * 8), {'font-size': 4})
	# Twin bee in slot 2 only: replace some graphics.
	if twinbee:
		more = read_characters(0x938e, 5, 4)
		for r in range(3):
			chars[r].update(more[r])
		if level >= 9:
			more = read_characters(0x939b, 5, 4)
			for r in range(3):
				chars[r].update(more[r])

	return chars

def output_charmap(chars, filename):
	img = Image.new('RGB', (0x900, 8 * 3))
	for region in range(3):
		for c, char in chars[region].items():
			img.paste(char, (c * 9, (2 - region) * 8))
	img.save(filename)
	return img

def debug_characters():
	out = Image.new('RGB', (0x900, 9 * 3 * levels - 1))
	for level in range(1, levels + 1):
		chars = load_charmap(level)
		row = output_charmap(chars, '/tmp/nemesis-chars-%x.png' % level)
		out.paste(row, (0, 9 * 3 * (level - 1)))
	out.save('/tmp/nemesis-chars.png')

def debug_mirror():
	out = svg()
	for x in range(0, 0x100, 4):
		out.add('%02x' % x, (x * 8, 0), {'font-size': 4})
	for level in range(1, levels + 1):
		chars = load_charmap(level) #, svg = out)
		for region in range(3):
			for c in chars[region]:
				out.add(chars[region][c], (8 * c, 8 + 8 * (2 - region) + 0x20 * level))
	out.save('/tmp/nemesis-mirror.svg', size = (0x800, 0x200))
# }}}

# Tiles {{{
def make_tile(chars, level, tile, codes = False):
	tilebase = (0x8ff0 if level in (0x5, 0x9, 0xa, 0xc) else 0x8000, 0xb)
	if codes:
		imgs = [np.zeros((4, 4), dtype = np.uint8) for _ in range(3)]
	else:
		imgs = [Image.new('RGB', (4 * 8, 4 * 8)) for _ in range(3)]
	for region in range(3):
		for ty in range(4):
			for tx in range(4):
				char = rom[addr2rom(tilebase[0] + 0x10 * tile + 4 * ty + tx, tilebase[1])]
				if char in chars[region]:
					if codes:
						imgs[region][ty][tx] = char
					else:
						imgs[region].paste(chars[region][char], (8 * tx, 8 * ty))
	return imgs

def debug_tiles():
	tilemap = [None] + [Image.new('RGB', (0x21 * 0x100 - 1, 0x21 * 3)) for _ in range(levels)]
	for level in range(1, levels + 1):
		used = level_tiles(level)
		chars = load_charmap(level)
		for c in range(0x100):
			tiles = make_tile(chars, level, c)
			for region in range(3):
				if (c, region) in used:
					tile = tiles[region]
				else:
					tile = Image.new('RGB', (0x20, 0x20), (128, 128, 128))
				tilemap[level].paste(tile, (0x21 * c, (2 - region) * 0x21))
	out = svg()
	for r in range(1, levels + 1):
		out.add(tilemap[r], (0, (r - 1) * (0x21 * 3 + 0x10)))
	out.save('/tmp/nemesis-tiles.svg', (0x2100, levels * (0x21 * 3 + 0x10) - 0x11))

def load_tiles(level, codes = False):
	chars = load_charmap(level)
	return [make_tile(chars, level, c, codes) for c in range(0x100)]
# }}}

# Levels {{{
def output_levels():
	special_location = (0x1c0, 0x1df, 0x1af, 0x1c0, 0x1ff,) # ?
	out = svg()
	maxx = 0
	level_g = {}
	enemies = debug_enemies()
	text_output = open('/tmp/nemesis-levels.txt', 'w')
	for level in range(1, levels + 1):
		chars = load_charmap(level)
		intro_len = read_word(0x4499 + level * 6, 0)
		level_len = read_word(0x4499 + level * 6 + 2, 0)
		boss_pos = read_word(0x4499 + level * 6 + 4, 0)
		print('level %x; %x %x %x' % (level, intro_len, level_len, boss_pos))
		if level_len - intro_len <= 0:
			if boss_pos == 0xffff:
				continue
			intro_len = boss_pos + 1
			level_len = boss_pos + 1
		if level_len > maxx:
			maxx = level_len
		level_pointers = (0x97de, 0xb)
		leveldata = (read_word(level_pointers[0] + 2 * level, level_pointers[1]), level_pointers[1])

		# Create text output.
		tiles = load_tiles(level, True)
		for y in range(22):
			line = []
			for x in range(intro_len // 4, level_len // 4):
				tile = rom[addr2rom(leveldata[0] + (x - intro_len // 4) * 6 + y // 4, leveldata[1])]
				line.extend(tiles[tile][0][y % 4, :])
			print(' '.join('%02x' % t for t in line), file = text_output)
		print(file = text_output)

		# Create graphical output.
		tiles = load_tiles(level)

		# create a len x 24 grid.
		img = Image.new('RGB', (level_len * 8, 0x16 * 8))
		for x in range(intro_len // 4, level_len // 4):
			for y in range(6):
				tile = rom[addr2rom(leveldata[0] + (x - intro_len // 4) * 6 + y, leveldata[1])]
				img.paste(tiles[tile][2 - (y // 2)], (x * 0x20, y * 0x20))
		level_g[level] = g()
		level_g[level].add(img, (0, 0))

		# Add cannons to level.
		cannon_addr = read_word(0x9262 + 2 * level, 2)
		while True:
			pos = read_word(cannon_addr, 2)
			if pos == 0xffff:
				break
			type = rom[addr2rom(cannon_addr + 2, 2)]
			y = type & 0x1f
			# The rest of type:
			# 20: ? (at top)
			# 40: red
			# 80: ? (not seen)
			bb = [None, 0x0f, 0x09, None, 0x0f, None, None, 0x0f, 0x0f, 0x09, 0x09, 0x09, 0x09]
			bt = [None, 0x1b, 0x1b, None, 0x1b, None, None, 0x1b, 0x1b, 0x1b, 0x1b, 0x1b, 0x1b]
			rb = [None, 0x09, 0x23, 0x0f, None, 0x0f, None, 0x09, 0x09, 0x23, 0x23, 0x23, 0x23]
			rt = [None, None, 0x15, 0x15, None, 0x39, None, 0x1b, 0x2d, 0x15, 0x15, 0x15, 0x15]
			blue = (type & 0xc0) == 0
			if blue:
				if type & 0x20 == 0:
					# blue at bottom
					sprite = bb[level]
				else:
					# blue at top
					sprite = bt[level]
			else:
				if type & 0x20 == 0:
					# red at bottom
					sprite = rb[level]
				else:
					# red at top
					sprite = rt[level]
			if sprite is None:
				print('defaulting on cannon characters!', level, pos, y, type)
				sprite = 0
			set = 2 - y // 8
			if level < len(enemies) and sprite < len(enemies[level]) and set < len(enemies[level][sprite]):
				level_g[level].add(enemies[level][sprite][set], (pos * 8, y * 8))
			else:
				level_g[level].add('?', (pos * 8, y * 8))
			if type & 0x80:
				# Anything with bit 7 set.
				level_g[level].add(custom_object('rect', {'x': pos * 8, 'y': y * 8, 'width': 16, 'height': 16, 'stroke': 'blue', 'fill': 'none'}), None)
			cannon_addr += 3

		# Add rectangles to show "other" enemies(?)
		eaddr = read_word(0x64fa + 2 * level, 1)
		while True:
			pos = read_word(eaddr, 1)
			if pos == 0xffff:
				break
			type = rom[addr2rom(eaddr + 2, 1)]
			idx = (0, 0, 1, 2)[type >> 6]
			y = type & 0x1f
			if level == 3:
				offset = (5, 5, 0, 2)[type >> 6]
				y += offset
			set = 2 - y // 8
			if level == 3:
				for i in range(10):
					print('stuff', 'level', level, 'y', y, 'data', 'type', idx, addr2rom(0x64d4 + idx * 10 + i, 1))
					c = rom[addr2rom(0x64d4 + idx * 10 + i, 1)]
					if c in chars[set]:
						level_g[level].add(chars[set][c], ((pos + i) * 8, y * 8))
					else:
						level_g[level].add(custom_object('rect', {'x': (pos + i) * 8, 'y': y * 8, 'width': 8, 'height': 8, 'stroke': 'none', 'fill': 'red'}), None)
			else:
				level_g[level].add(custom_object('rect', {'x': pos * 8, 'y': y * 8, 'width': 32, 'height': 32, 'stroke': 'yellow', 'fill': 'none'}), None)
			eaddr += 3

		# Add rectangles to show secret level triggers.
		secrets = {
			1: [(0x0fc, 0x88, 2)],
			2: [(0x190, 0x88, 1)],
			3: [(0x12a, 0x30, 1)],
			4: [(0x0c0, 0x10, 3), (0x104, 0x10, 4)],
			7: [(0x177, 0x38, 1)],
		}
		color = {1: 'blue', 2: 'yellow', 3: 'orange', 4: 'red'}
		if level in secrets:
			for x, y, t in secrets[level]:
				level_g[level].add(custom_object('rect', {'x': (x - 1) * 8, 'y': y, 'width': 16, 'height': 16, 'stroke': color[t], 'fill': 'none'}), None)

		# Bonus items.
		if level >= 9:
			addr = read_word(0xb2d2 + level * 2, 0xc)
			while True:
				y = rom[addr2rom(addr, 0xc)]
				x = read_word(addr + 1, 0xc)
				addr += 3
				if (x, y) == (0xffff, 0xff):
					break
				flags = y & 7
				y &= ~7
				set = y // (8 * 8)
				level_g[level].add(enemies[level][0x38 if flags & 3 else 0x37][set], (x * 8, y), style = ({} if flags & 4 else {'opacity': '.6'}))
				if flags & 2:
					level_g[level].add(custom_object('rect', {'x': x * 8, 'y': y, 'width': 16, 'height': 16, 'stroke': 'red', 'fill': 'none'}), None)

		out.add(level_g[level], (0, (6 * 4 * 8 - 8) * (level - 1)))
	for l in special_location:
		out.add('!', (l * 8, 0))
	out.save('/tmp/nemesis-levels.svg', (maxx * 8, levels * (6 * 4 * 8 - 8) - 8))
	text_output.close()
	# }}}

def level_tiles(level):
	intro_len = read_word(0x4499 + level * 6, 0)
	level_len = read_word(0x4499 + level * 6 + 2, 0)
	if level_len - intro_len <= 0:
		return set()
	level_pointers = (0x97de, 0xb)
	leveldata = (read_word(level_pointers[0] + 2 * level, level_pointers[1]), level_pointers[1])

	# Return all the tiles that are used in the level. Values are tuples of (tile_id, screen_region).
	ret = set()
	for x in range(((level_len + 4) - intro_len) // 4):
		for y in range(6):
			tile = rom[addr2rom(leveldata[0] + x * 6 + y, leveldata[1])]
			ret.add((tile, 2 - y // 2))
	return ret

def debug_enemies():
	ret = [None]
	out = svg()
	for n in range(0x45): # looking at the output, anything above 0x45 is junk.
		out.add('%02x' % n, (n * 0x11, -0x10))
	for level in range(1, levels + 1):
		ret.append([])
		chars = load_charmap(level)
		for i in range(0x45):
			current = [Image.new('RGB', (0x10, 0x10)) for _ in range(3)]
			addr = addr2rom(0x91d1, 5) + i * 4
			for c in range(3):
				for y in range(2):
					for x in range(2):
						char = rom[addr + y * 2 + x]
						if char in chars[c]:
							current[c].paste(chars[c][rom[addr + y * 2 + x]], (x * 8, y * 8))
				out.add(current[c], (i * 0x11, (level - 1) * 0x43 + c * 0x11))
			ret[-1].append(current)
	out.save('/tmp/nemesis-enemies-2x2.svg', (0x45 * 0x11 - 1, levels * 0x43 - 0x11))
	return ret

debug_enemies()
debug_tiles()
debug_mirror()
output_levels()
# vim: set foldmethod=marker :
