import sys
import gzip
import struct
from collections import OrderedDict
from redeclipse.enums import EntType, Faces, VTYPE, OCT, TextNum
from redeclipse.objects import VSlot, SlotShaderParam, cube, SurfaceInfo
from redeclipse.entities import Entity
import simplejson as json
import logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

MAXSTRLEN = 512

def tb(str_or_bytes):
    if isinstance(str_or_bytes, str):
        return str.encode(str_or_bytes)
    else:
        return str_or_bytes


class Map:

    def __init__(self, magic, version, headersize, meta, map_vars, texmru, ents, vslots, chg, worldroot):
        self.magic = magic
        self.version = version
        self.headersize = headersize
        self.meta = meta
        self.map_vars = map_vars
        self.texmru = texmru
        self.ents = ents
        self.vslots = vslots
        self.chg = chg
        self.world = worldroot

    def write(self, path):
        log.info('WRITING')
        handle = gzip.open(path, 'wb')
        self.write_str(handle, tb(self.magic), null=False)
        # Write the version
        self.write_int(handle, self.version)
        # Write the header size (Surely some way to calc from self.meta?)
        self.write_int(handle, self.headersize)
        # Write the header block
        self.meta['numents'] = len(self.ents)
        for key in self.meta:
            if key == 'gameident':
                self.write_str(handle, tb(self.meta[key]))
            else:
                self.write_int(handle, self.meta[key])

        # Write the map vars
        for key in self.map_vars:
            var_name = key
            value = self.map_vars[key]
            var_type = type(self.map_vars[key]).__name__

            self.write_int(handle, len(var_name))
            self.write_str(handle, var_name)

            if var_type == 'int':
                self.write_int(handle, 0)
                self.write_int(handle, value)
            elif var_type == 'float':
                self.write_int(handle, 1)
                self.write_float(handle, value)
            elif var_type in ('bytes', 'str'):
                self.write_int(handle, 2)
                self.write_int(handle, len(value))
                self.write_str(handle, value)
            else:
                raise Exception("Can't handle " + var_type)

        # Texmru
        self.write_ushort(handle, len(self.texmru))  # nummru
        for value in self.texmru:
            self.write_ushort(handle, value)

        # Entities
        self.write_ents(handle, self.ents)

        # Textures
        self.write_vslots(handle, self.vslots, self.chg)

        # World
        self.savechildren(handle, self.world)

    def write_custom(self, handle, fmt, data):
        handle.write(struct.pack(fmt, *data))

    def write_char(self, handle, char):
        handle.write(struct.pack('B', char))

    def write_int_as_chr(self, handle, data):
        handle.write(struct.pack('c', str.encode(chr(data))))

    def write_int(self, handle, value):
        if isinstance(value, int):
            handle.write(struct.pack('i', value))
        else:
            handle.write(struct.pack('i', value.value))

    def write_ushort(self, handle, value):
        handle.write(struct.pack('H', value))

    def write_float(self, handle, value):
        handle.write(struct.pack('f', value))

    def write_str(self, handle, value, null=True):
        strlen = len(value)
        if null:
            strlen += 1

        fmt = '%ds' % strlen
        handle.write(struct.pack(fmt, value))

    def write_ents(self, handle, ents):
        for ent in ents:
            # (x, y, z, etype, a, b, c) = self.read_custom('fffcccc', sizeof_entbase)
            self.write_custom(
                handle,
                'fffcccc',
                ent.serialize()
            )

            self.write_int(handle, len(ent.attrs))
            for at in ent.attrs:
                self.write_int(handle, at)

            self.write_int(handle, len(ent.links))
            for ln in ent.links:
                self.write_int(handle, ln)

    def write_vslots(self, handle, vslots, chg):
        for num in chg:
            self.write_int(handle, num)
            if num < 0:
                pass
            else:
                raise NotImplementedError()

    def write_vslot(self, vs, changed):
        pass

    def savechildren(self, handle, cube_arr, indent=0):
        for i, c in enumerate(cube_arr):
            if indent < 4:
                log.info('%s %s', indent, i)
            self.savec(handle, c, indent=indent)

    def savec(self, handle, c, indent=0):
        """Inverse of loadc"""

        self.write_int_as_chr(handle, c.octsav)
        if c.octsav & 0x7 == OCT.OCTSAV_CHILDREN.value:
            self.savechildren(handle, c.children, indent=indent+1)
            return
        elif c.octsav & 0x7 == OCT.OCTSAV_EMPTY.value:
            pass # Nothing to write
        elif c.octsav & 0x7 == OCT.OCTSAV_SOLID.value:
            pass # Nothing to write, simply that c is solid
        elif c.octsav & 0x7 == OCT.OCTSAV_NORMAL.value:
            self.write_custom(handle, 'BBBBBBBBBBBB', c.edges)
        elif c.octsav & 0x7 == OCT.OCTSAV_LODCUBE.value:
            # Nothing to do, this just set c.children, which we know
            # from other sources.
            pass
        else:
            sys.exit(42)
            return

        for i, t in enumerate(c.texture):
            if isinstance(t, TextNum):
                self.write_ushort(handle, t.value)
            else:
                self.write_ushort(handle, t)

        if c.octsav & 0x40:
            self.write_ushort(handle, c.material)
        if c.octsav & 0x80:
            self.write_int_as_chr(handle, c.merged)
        if c.octsav & 0x20:
            self.write_int_as_chr(handle, c.surfmask)
            self.write_int_as_chr(handle, c.totalverts)

            for i in range(6):
                if not c.surfmask & (1<<i):
                    pass
                else:
                    surfinfo = c.ext.surfaces[i]

                    self.write_char(handle, surfinfo.lmid[0])
                    self.write_char(handle, surfinfo.lmid[1])
                    self.write_char(handle, surfinfo.verts)
                    self.write_char(handle, surfinfo.numverts)

                    if surfinfo.verts == 0:
                        continue
                    else:
                        raise NotImplementedError("Gross out")

    def to_dict(self):
        return {
            'magic': bytes.decode(self.magic),
            'version': self.version,
            'headersize': self.headersize,
            'meta': [(key, bytes.decode(value) if isinstance(value, bytes) else value) for (key, value) in self.meta.items()],
            'map_vars': [(bytes.decode(key), bytes.decode(value) if isinstance(value, bytes) else value) for (key, value) in self.map_vars.items()],
            'texmru': self.texmru,
            'entities': [ent.to_dict() for ent in self.ents],
            'world': (x.to_dict() for x in self.world),
            'vslots': (x.to_dict() for x in self.vslots),
            'chg': self.chg,
        }

    def to_json(self):
        return json.dumps(self.to_dict(), iterable_as_array=True)
    @classmethod
    def from_dict(cls, data):
        # TODO
        meta = OrderedDict()
        for (key, value) in data['meta']:
            meta[key] = value

        map_vars = OrderedDict()
        for (key, value) in data['map_vars']:
            if isinstance(value, str):
                map_vars[str.encode(key)] = str.encode(value)
            else:
                map_vars[str.encode(key)] = value

        # TODO
        world = {}

        m = Map(
            magic=str.encode(data['magic']),
            version=data['version'],
            headersize=data['headersize'],
            meta=meta,
            map_vars=map_vars,
            texmru=data['texmru'],
            ents=[Entity.from_dict(x) for x in data['entities']],
            vslots=[VSlot.from_dict(x) for x in data['vslots']],
            chg=data['chg'],
            worldroot=world,
        )

        return m


class MapParser(object):

    def _read_custom(self, pattern, width):
        val = struct.unpack(pattern, self.bytes[self.index:self.index + width])
        self.index += width
        return val

    def read_int(self):
        val = self._read_custom('i', 4)[0]
        return val

    def read_char(self):
        val = self._read_custom('B', 1)[0]
        return val

    def read_custom(self, pattern, width):
        val = self._read_custom(pattern, width)
        return val

    def read_float(self):
        val = self._read_custom('f', 4)[0]
        return val

    def read_ushort(self):
        val = self._read_custom('H', 2)[0]
        return val

    def read_str(self, strlen, null=True):
        if null:
            # Strings are null terminated
            strlen += 1
        fmt = '%ds' % strlen
        data = struct.unpack(fmt, self.bytes[self.index:self.index + strlen])
        self.index += strlen
        if null:
            return data[0][0:-1]
        return data[0]

    def loadvslots(self, numvslots):
        prev = [-1] * numvslots
        vslots = []
        chg = []
        while numvslots > 0:
            changed = self.read_int()
            chg.append(changed)
            if changed < 0:
                for i in range(-changed):
                    vslots.append(VSlot(None, len(vslots)))
                numvslots += changed
            else:
                prev.append(self.read_int())
                self.loadvslot(VSlot(None, len(vslots)), changed)
                numvslots -= 1


        for idx, v in enumerate(vslots):
            if 0 <= idx < numvslots:
                vslots[prev[idx]]._next = vslots[idx]

        return vslots, chg

    def loadvslot(self, vs, changed):
        vs.changed = changed
        if vs.changed & (1<<VTYPE.VSLOT_SHPARAM.value):
            flags = self.read_ushort()
            numparams = flags & 0x7FFF
            for i in range(numparams):
                ssp = SlotShaderParam()
                nlen = self.read_ushort()
                if nlen >= MAXSTRLEN:
                    log.error("Cannot handle")
                    sys.exit()

                name = self.read_str(nlen, null=False)
                ssp.name = name
                ssp.loc = -1
                ssp.val = [
                    self.read_float(),
                    self.read_float(),
                    self.read_float(),
                    self.read_float(),
                ]
                if flags & 0x8000:
                    ssp.palette = self.read_int()
                    ssp.palindex = self.read_int()
                else:
                    ssp.palette = 0
                    ssp.palindex = 0
        if vs.changed & (1<<VTYPE.VSLOT_SCALE.value):
            vs.scale = self.read_float()
        if vs.changed & (1<<VTYPE.VSLOT_ROTATION.value):
            vs.rotation = self.read_int()
        if vs.changed & (1<<VTYPE.VSLOT_OFFSET.value):
            vs.offset_x = self.read_int()
            vs.offset_y = self.read_int()
        if vs.changed & (1<<VTYPE.VSLOT_SCROLL.value):
            vs.scroll_x = self.read_int()
            vs.scroll_y = self.read_int()
        if vs.changed & (1<<VTYPE.VSLOT_LAYER.value):
            vs.layer = self.read_int()
        if vs.changed & (1<<VTYPE.VSLOT_ALPHA.value):
            vs.alphafront = self.read_float()
            vs.alphaback = self.read_float()

        if vs.changed & (1<<VTYPE.VSLOT_COLOR.value):
            vs.colorscale = [
                self.read_float(),
                self.read_float(),
                self.read_float()
            ]
        if vs.changed & (1<<VTYPE.VSLOT_PALETTE.value):
            vs.palette = self.read_int()
            vs.palindex = self.read_int()
        if vs.changed & (1<<VTYPE.VSLOT_COAST.value):
            vs.coastscale = self.read_float()

    def loadchildren(self, size, failed, indent=0):
        cube_arr = cube.newcubes(Faces.F_EMPTY, 0)
        for i in range(8):
            failed, c_x = self.loadc(
                cube_arr[i], # c
                size,
                failed,
                indent=indent
            )
            cube_arr[i] = c_x

            if failed:
                break
        return cube_arr

    def loadc(self, c, size, failed, indent=0):
        """Loads a single cube? Or rather, based on C, processes it into a cube object?"""
        octsav = self.read_char()
        c.octsav = octsav
        c.haschildren = False
        if octsav & 0x7 == OCT.OCTSAV_CHILDREN.value:
            c.children = self.loadchildren(size>>1, failed, indent=indent+1)
            return False, c
        elif octsav & 0x7 == OCT.OCTSAV_EMPTY.value:
            c.setfaces(Faces.F_EMPTY)
        elif octsav & 0x7 == OCT.OCTSAV_SOLID.value:
            c.setfaces(Faces.F_SOLID)
        elif octsav & 0x7 == OCT.OCTSAV_NORMAL.value:
            c.edges = self.read_custom('BBBBBBBBBBBB', 12)
        elif octsav & 0x7 == OCT.OCTSAV_LODCUBE.value:
            c.haschildren = True
        else:
            failed = True
            return failed, c

        c.texture = []
        for i in range(6):
            c.texture.append(self.read_ushort())

        if octsav & 0x40:
            c.material = self.read_ushort()
        if octsav & 0x80:
            c.merged = self.read_char()
        if octsav & 0x20:
            surfmask = self.read_char()
            c.surfmask = surfmask
            totalverts = self.read_char()
            c.totalverts = totalverts
            c.newcubeext(totalverts, False)
            # offset = 0
            for i in range(6):
                if not surfmask & (1<<i):
                    c.ext.surfaces.append(None)
                else:
                    c.ext.surfaces.append(
                        SurfaceInfo(
                            self.read_char(),
                            self.read_char(),
                            self.read_char(),
                            self.read_char()
                        )
                    )

                    surf = c.ext.surfaces[i]
                    vertmask = surf.verts
                    numverts = surf.totalverts()
                    if not numverts:
                        surf.verts = 0
                        continue

                    raise NotImplementedError("Gross in")

        return failed, c

    def loadents(self, numents):
        sizeof_entbase = 16
        ents = []
        for i in range(int(numents)):
            (x, y, z, etype, a, b, c) = self.read_custom('fffcccc', sizeof_entbase)

            # This says reserved but we've seen values in it so...
            reserved = [
                ord(a),
                ord(b),
                ord(c)
            ]

            numattr = self.read_int()
            attrs = []
            for j in range(numattr):
                attrs.append(self.read_int())

            link_count = self.read_int()
            links = []
            for j in range(link_count):
                links.append(self.read_int())

            e = Entity(x, y, z, EntType(ord(etype)), attrs, links, reserved)
            ents.append(e)
        return ents

    def read(self, base_path):
        """Load the specified map"""
        self.base_path = base_path
        self.index = 0

        with gzip.open(base_path) as handle:
            self.bytes = handle.read()

        magic = self.read_str(4, null=False)
        if magic not in (b'MAPZ', b'BFGZ'):
            raise Exception("Not a mapz file")


        log.debug('Loading map: %s', base_path)
        log.debug('Header Magic: %s', magic)
        version = self.read_int()
        log.debug('Version: %s', version)
        headersize = self.read_int()
        log.debug('Header Size: %s', headersize)

        meta_keys = ('worldsize', 'numents', 'numpvs',
                     'lightmaps', 'blendmap', 'numvslots',
                     'gamever', 'revision')
        #'gameident', 'numvars')
        meta = OrderedDict()
        for k in meta_keys:
            meta[k] = self.read_int()

        # char[4], null=True
        meta['gameident'] = self.read_str(3)
        meta['numvars'] = self.read_int()
        log.debug(meta)
        log.debug('Header Worldsize: %s', meta['worldsize'])


        map_vars = OrderedDict()
        for i in range(meta['numvars']):
            # +1 for null term string
            var_name_len = self.read_int()
            var_name = self.read_str(var_name_len)
            var_type = self.read_int()

            # String
            if var_type == 2:
                var_len = self.read_int()
                var_val = self.read_str(var_len)
            elif var_type == 1:
                var_val = self.read_float()
            elif var_type == 0:
                var_val = self.read_int()
            else:
                # Cannot recover
                raise Exception("Don't know how to handle map prop type %s", var_type)

            map_vars[var_name] = var_val

        texmru = []
        nummru = self.read_ushort()
        log.debug('Nummru %s', nummru)
        for i in range(nummru):
            texmru.append(self.read_ushort())

        # Entities
        log.debug('Header.numents %s', meta['numents'])
        ents = self.loadents(meta['numents'])
        log.debug("Loaded %s entities", len(ents))

        # Textures?
        vslots, chg = self.loadvslots(meta['numvslots'])
        log.debug("Loaded %s vslots", len(vslots))

        # arggghhh
        worldroot = []
        failed = False
        log.debug("Loadchildren")
        worldroot = self.loadchildren(
            meta['worldsize']>>1,
            failed
        )

        cube.validatec(worldroot, meta['worldsize'] >> 1)

        worldscale = 0
        while 1<<worldscale < meta['worldsize']:
            worldscale += 1
        # log.debug("Worldscale %s" % worldscale)

        # log.debug("failed: %s" % (1 if failed else 0))
        # if not failed:
            # # Not sure this even works, but no need to implement since
            # # we're fine to dump unlit maps.
            # log.debug('Lightmaps: %s' % meta['lightmaps'])
            # TODO

        m = Map(magic, version, headersize, meta, map_vars, texmru, ents, vslots, chg,
                worldroot)
        return m
