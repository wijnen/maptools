# Python-svg
# vim: set foldmethod=marker :

'''Module for creating svg images.

This module is meant for easily creating svg images for use with map generation scripts.

API:

Svg(objects = ())					# Constructor. Given objects are added using add(obj, pos = (0, 0)).
	save(filename)					# Save svg file to disk
	add(obj, style = None, pos = None, id = None)	# Add an object.

text(text, style = None)				# Create a new text object.
image(PIL.Image, style = None)				# Create a new image object.
Object(objtype, attrs = {}, content = '', style = None)	# Create a custom object; objtype must be a valid svg element tag.
'''

import io
import base64
import PIL.Image

class Object:
	count = 0
	def __init__(self, id):
		if id is None:
			id = 'obj%04x' % Object.count
			Object.count += 1
		self.id = id
	def _register(self, index):
		if self.id not in index:
			index[self.id] = {'object': self, 'count': 0, 'defs': 0}
		index[self.id]['count'] += 1
	def _defsregister(self, index, num):
		pass
	def _add_style_pos(self, style, pos):
		ret = ''
		if style is not None and len(style) > 0:
			ret += " style='" + ';'.join('%s:%s' % (key, value) for key, value in style.items()) + "'"
		if pos is not None:
			ret += " x='%f' y='%f'" % tuple(pos)
		return ret
	def _mksvg(self, style, tag, pos, attrs, content = None, id = True):
		attrs = attrs.copy()	# Don't change caller's object.
		ret = '<' + tag
		if id and self.id is not None:
			attrs['id'] = self.id
		ret += self._add_style_pos(style, pos)
		if len(attrs) > 0:
			ret += ''.join(" %s='%s'" % (key, value) for key, value in attrs.items())
		if content is None:
			ret += '/>'
		else:
			ret += '>' + content + '</' + tag + '>'
		return ret

class g(Object):
	'''This class contains a group of objects. It can be an svg "g" object, including a layer, or an svg document.'''
	def __init__(self, objects = (), style = None, id = None):
		super().__init__(id)
		self.style = style
		self.objects = []
		for o in objects:
			self.add(o)
	def _objects(self, obj_index):
		'''Return all the objects that this group contains, for use in _svg() and svg()'''
		ret = ''
		for o in self.objects:
			# Get record from index.
			obj = o['object']
			# Use reference if it is reused.
			if obj.id in obj_index and obj_index[obj.id]['count'] - obj_index[obj.id]['defs'] > 1:
				ret += ("<use xlink:href='#%s'" % obj.id) + self._add_style_pos(o['style'], o['pos']) + '/>\n'
			else:
				ret += o['object']._svg(o['style'], o['pos'], obj_index) + '\n'
		return ret
	def _svg(self, style, pos, obj_index): 
		if self.style is not None:
			s = style
			style = self.style.copy()
			style.update(s)
		attrs = {}
		if pos is not None:
			attrs['transform'] = 'translate(%f,%f)' % (pos)
		return self._mksvg(style, 'g', None, attrs, self._objects(obj_index))
	def _register(self, index):
		super()._register(index)
		for o in self.objects:
			o['object']._register(index)
	def _defsregister(self, index, num):
		for o in self.objects:
			if index[o['object'].id]['count'] > 1:
				extra = 1
			else:
				extra = 0
			index[o['object'].id]['defs'] += num + extra
			o['object']._defsregister(index, num + extra)
	def svg(self, size, attrs = {}, style = {}):
		'''Create an svg file from the objects. Return the file as a string.
		The size is the physical size of the page (2-tuple), in mm.'''
		# First, find all the objects and figure out which ones are used more than once.
		obj_index = {}
		# Build use counters.
		for o in self.objects:
			o['object']._register(obj_index)
		# Correct for objects in defs.
		for o in self.objects:
			o['object']._defsregister(obj_index, 0)
		# Create the output.
		ret = ''
		# If there are objects that are reused, add a defs element.
		if any(obj_index[o]['count'] > 1 for o in obj_index):
			ret += '<defs>\n'
			for o in obj_index:
				if obj_index[o]['count'] - obj_index[o]['defs'] > 1:
					ret += obj_index[o]['object']._svg({}, None, {}) + '\n'
			ret += '</defs>\n'
		ret += self._objects(obj_index)
		# Add default attributes.
		attrs = attrs.copy() # Don't change caller's object.
		if 'width' not in attrs:
			attrs['width'] = '%fmm' % size[0]
		if 'height' not in attrs:
			attrs['height'] = '%fmm' % size[1]
		if 'viewbox' not in attrs:
			attrs['viewbox'] = '%f %f %f %f' % (0, 0, size[0], size[1])
		if 'xmlns' not in attrs:
			attrs['xmlns'] = 'http://www.w3.org/2000/svg'
		if 'xmlns:xlink' not in attrs:
			attrs['xmlns:xlink'] = 'http://www.w3.org/1999/xlink'
		if 'version' not in attrs:
			attrs['version']='1.1'
		# Apply top level style.
		if self.style is not None:
			s = style
			style = self.style.copy()
			style.update(s)
		# Output 
		header = '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n'
		return header + self._mksvg(style, 'svg', None, attrs, '\n' + ret, id = None)
	def add(self, obj, pos = None, style = None):
		# Automatically convert objects into Objects.
		if not isinstance(obj, Object):
			detect = {str: text, PIL.Image.Image: image}
			for d in detect:
				if isinstance(obj, d):
					obj = detect[d](obj)
					break
			else:
				raise TypeError('object to add %s has invalid type' % obj)
		self.objects.append({'object': obj, 'pos': pos, 'style': style})

# Alias g as svg.
svg = g

class text(Object):
	def __init__(self, text, id = None):
		super().__init__(id)
		self.text = text
	def _svg(self, style, pos, obj_index):
		return self._mksvg(style, 'text', pos, {}, self.text)

class image(Object):
	def __init__(self, image, id = None):
		super().__init__(id)
		self.image = image
		self.size = image.size
		f = io.BytesIO()
		image.save(f, 'png')
		self.url = 'data:image/png;base64,' + base64.b64encode(f.getbuffer()).decode('utf-8')
	def _svg(self, style, pos, obj_index):
		return self._mksvg(style, 'image', pos, {'xlink:href': self.url, 'width': self.size[0], 'height': self.size[1]})
