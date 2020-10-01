import struct
import pkg_db
from dataclasses import dataclass, fields
import numpy as np
import binascii
import os
import fbx
import pyfbx_jo as pfb
import gf

version = '2_9_2_1_all'


@dataclass
class Stride12Header:
    EntrySize: np.uint32 = np.uint32(0)
    StrideLength: np.uint32 = np.uint32(0)
    DeadBeef: np.uint32 = np.uint32(0)


@dataclass
class LODSubmeshEntry:
    Offset: np.uint32 = np.uint32(0)
    FacesLength: np.uint32 = np.uint32(0)
    SecondIndexRef: np.uint16 = np.uint16(0)
    EntryType: np.uint16 = np.uint16(0)


class File:
    def __init__(self, name=None, uid=None, pkg_name=None):
        self.name = name
        self.uid = uid
        self.pkg_name = pkg_name

class HeaderFile(File):
    def __init__(self, header=None):
        super().__init__()
        self.header = header

    def get_header(self):
        if self.header:
            print('Cannot get header as header already exists.')
            return
        else:
            if not self.name:
                self.name = gf.get_file_from_hash(self.uid)
            pkg_name = gf.get_pkg_name(self.name)
            header_hex = gf.get_hex_data(f'{test_dir}/{pkg_name}/{self.name}.bin')
            return get_header(header_hex, Stride12Header())


def get_header(file_hex, header):
    # The header data is 0x16F bytes long, so we need to x2 as python reads each nibble not each byte

    for f in fields(header):
        if f.type == np.uint32:
            flipped = "".join(gf.get_flipped_hex(file_hex, 8))
            value = np.uint32(int(flipped, 16))
            setattr(header, f.name, value)
            file_hex = file_hex[8:]
        elif f.type == np.uint16:
            flipped = "".join(gf.get_flipped_hex(file_hex, 4))
            value = np.uint16(int(flipped, 16))
            setattr(header, f.name, value)
            file_hex = file_hex[4:]
    return header


test_dir = 'C:/d2_output/'


def get_referenced_file(file):
    pkg_name = file.pkg_name
    if not pkg_name:
        return None, None, None
    entries_refpkg = {x: y for x, y in pkg_db.get_entries_from_table(pkg_name, 'FileName, RefPKG')}
    entries_refid = {x: y for x, y in pkg_db.get_entries_from_table(pkg_name, 'FileName, RefID')}
    if file.name not in entries_refpkg.keys():
        return None, None, None
    ref_pkg_id = entries_refpkg[file.name][2:]
    ref_pkg_name = gf.get_pkg_name(f'{ref_pkg_id}-')
    if not ref_pkg_name:
        return None, None, None
    entries_filetype = {x: y for x, y in pkg_db.get_entries_from_table(ref_pkg_name, 'FileName, FileType')}

    ref_file_name = f'{ref_pkg_id}-' + entries_refid[file.name][2:]
    return ref_pkg_name, ref_file_name, entries_filetype[ref_file_name]


def get_model(model_file_hash):
    """
    Given a model file:
    - open the model file and identify the model data file
    - open the model data file
    - identify the faces and 8verts files
    - get all faces data
    - get all 8verts data
    - slim down faces data to fit the number of verts as otherwise it will crash
    - combine the faces and vert data into the obj
    - write obj
    """
    print(model_file_hash)
    pkg_db.start_db_connection(version)
    model_file = gf.get_file_from_hash(model_file_hash)
    model_data_file = get_model_data_file(model_file)
    print(f'1: {model_file} 2: {model_data_file}')
    submeshes_verts, submeshes_faces = get_verts_faces_data(model_data_file, version)
    obj_strings = []
    max_vert_used = 0
    # all_verts_str = ''  # joined obj
    # all_faces_str = ''  # joined obj
    for index_2 in range(len(submeshes_verts.keys())):
        for index_3 in range(len(submeshes_verts[index_2])):
            adjusted_faces_data, max_vert_used = adjust_faces_data(submeshes_faces[index_2][index_3], max_vert_used)
            obj_str = f'o {model_file_hash}_0_{index_2}_{index_3}\n'  # separated obj
            shifted_faces = shift_faces_down(adjusted_faces_data)
            obj_str += get_obj_str(adjusted_faces_data, submeshes_verts[index_2][index_3])  # replace with obj_str = for separated obj, otherwise verts_str, faces_str = for joined obj
            obj_strings.append(obj_str)  # separated obj
            # all_verts_str += verts_str  # joined obj
            # all_faces_str += faces_str  # joined obj
            write_fbx(shifted_faces, submeshes_verts[index_2][index_3], f'{model_file_hash}_0_{index_2}_{index_3}')
            write_obj(obj_str, f'{model_file_hash}_0_{index_2}_{index_3}')
    # obj_strings = f'o {model_file_hash}\n' + all_verts_str + all_faces_str  # joined obj
    write_obj(obj_strings, model_file_hash)


def shift_faces_down(faces_data):
    a_min = faces_data[0][0]
    for f in faces_data:
        for i in f:
            if i < a_min:
                a_min = i
    for i, f in enumerate(faces_data):
        for j, x in enumerate(f):
            faces_data[i][j] -= a_min - 1
    return faces_data


def adjust_faces_data(faces_data, max_vert_used):
    new_faces_data = []
    all_v = []
    for face in faces_data:
        for v in face:
            all_v.append(v)
    starting_face_number = min(all_v) -1
    all_v = []
    for face in faces_data:
        new_face = []
        for v in face:
            new_face.append(v - starting_face_number + max_vert_used)
            all_v.append(v - starting_face_number + max_vert_used)
        new_faces_data.append(new_face)
    return new_faces_data, max(all_v)


def get_verts_faces_data(model_data_file,version):
    all_faces_data = []
    all_pos_verts_data = []
    all_uv_verts_data = []
    all_verts_data = []
    # pkg_db.start_db_connection(version)
    faces_files, pos_verts_files, uv_verts_files, model_data_hex = get_faces_verts_files(model_data_file)
    if not faces_files or not pos_verts_files:
        return None, None
    for i, faces_file in enumerate(faces_files):
        pos_verts_file = pos_verts_files[i]
        faces_data = get_faces_data(faces_file)
        if not pos_verts_file:
            return None, None
        pos_verts_data = get_verts_data(pos_verts_file)
        # Even though this may be None it should be okay.
        uv_verts_data = None
        if len(uv_verts_files) == len(pos_verts_files):
            uv_verts_file = pos_verts_files[i]
            uv_verts_data = get_verts_data(uv_verts_file)
            all_uv_verts_data.append(uv_verts_data)
        if not pos_verts_data:
            return None, None
        if not faces_data:
            return None, None
        all_faces_data.append(faces_data)
        all_pos_verts_data.append(pos_verts_data)
        # verts_data = verts_8_data + verts_20_data
        if uv_verts_data:
            if len(uv_verts_data) != len(pos_verts_data):
                verts_data = pos_verts_data
            else:
                verts_data = [pos_verts_data[i] + uv_verts_data[i] for i in range(len(pos_verts_data))]
        else:
            verts_data = pos_verts_data
        all_verts_data.append(verts_data)
    submeshes_faces, submeshes_entries = separate_submeshes_remove_lods(model_data_hex, all_faces_data)
    submeshes_verts = {x: [] for x in submeshes_faces.keys()}
    for i in submeshes_faces.keys():
        for j, faces in enumerate(submeshes_faces[i]):
            if submeshes_entries[i][j].EntryType == 769:
                submeshes_verts[i].append(trim_verts_data(all_verts_data[i], faces))
            elif submeshes_entries[i][j].EntryType == 770:
                submeshes_verts[i].append(trim_verts_data(all_verts_data[i], faces))

    return submeshes_verts, submeshes_faces


def get_model_data_file(model_file):
    pkg_name = gf.get_pkg_name(model_file)
    if not pkg_name:
        return None
    model_hex = gf.get_hex_data(f'{test_dir}/{pkg_name}/{model_file}.bin')
    model_data_hash = model_hex[16:24]
    return gf.get_file_from_hash(model_data_hash)


def get_faces_verts_files(model_data_file):
    faces_files = []
    pos_verts_files = []
    uv_verts_files = []
    pkg_name = gf.get_pkg_name(model_data_file)
    if not pkg_name:
        return None, None, None, None
    try:
        model_data_hex = gf.get_hex_data(f'{test_dir}/{pkg_name}/{model_data_file}.bin')
    except FileNotFoundError:
        print(f'No folder found for file {model_data_file}. Likely need to unpack it or design versioning system.')
        return None, None, None, None
    split_hex = model_data_hex.split('BD9F8080')[-1]
    model_count = int(gf.get_flipped_hex(split_hex[:4], 4), 16)
    relevant_hex = split_hex[32:]
    for i in range(model_count):
        faces_hash = gf.get_flipped_hex(relevant_hex[32*i:32*i+8], 8)
        pos_verts_file = gf.get_flipped_hex(relevant_hex[32*i+8:32*i+16], 8)
        uv_verts_file = gf.get_flipped_hex(relevant_hex[32*i+16:32*i+24], 8)
        if faces_hash == '' or pos_verts_file == '' or uv_verts_file == '':
            return None, None, None, None
        for j, hsh in enumerate([faces_hash, pos_verts_file, uv_verts_file]):
            hf = HeaderFile()
            hf.uid = gf.get_flipped_hex(hsh, 8)
            hf.name = gf.get_file_from_hash(hf.uid)
            hf.pkg_name = gf.get_pkg_name(hf.name)
            if j == 0:
                faces_files.append(hf)
            elif j == 1:
                hf.header = hf.get_header()
                # print(f'Position file {hf.name} stride {hf.header.StrideLength}')
                pos_verts_files.append(hf)
            elif j == 2:
                if not hf.pkg_name:
                    continue
                hf.header = hf.get_header()
                # print(f'UV file {hf.name} stride {hf.header.StrideLength}')
                uv_verts_files.append(hf)

    return faces_files, pos_verts_files, uv_verts_files, model_data_hex


def separate_submeshes_remove_lods(model_data_hex, all_faces_data):
    """
    If entry is a submesh, I believe the range is just from Offset to Offset + FacesLength, where FacesLength/3 is the number of final faces
    If entry is LOD, range is the same where FacesLength/3 is the number of removed faces.
    Hence, we can pull all the stuff we want out by just separating [Offset:Offset + FacesLength]
    """
    unk_entries_count = int(gf.get_flipped_hex(model_data_hex[80*2:80*2 + 8], 4), 16)
    unk_entries_offset = 96

    end_offset = unk_entries_offset + unk_entries_count * 8
    end_place = int(model_data_hex[end_offset*2:].find('BD9F8080')/2)
    useful_entries_count = int(gf.get_flipped_hex(model_data_hex[(end_offset + end_place + 4)*2:(end_offset + end_place + 6)*2], 4), 16)
    useful_entries_offset = end_offset + end_place + 20
    useful_entries_length = useful_entries_count * 12
    useful_entries_hex = model_data_hex[useful_entries_offset*2:useful_entries_offset*2 + useful_entries_length*2]
    useful_entries = [useful_entries_hex[i:i+24] for i in range(0, len(useful_entries_hex), 24)]

    submesh_entries = []
    ret_sub_entries = {}
    for e in useful_entries:
        entry = get_header(e, LODSubmeshEntry())
        # The most likely thing for 770 is that it uses the 20 verts file.
        if entry.EntryType == 769 or entry.EntryType == 770:
            submesh_entries.append(entry)
            if entry.SecondIndexRef not in ret_sub_entries.keys():
                ret_sub_entries[entry.SecondIndexRef] = []
            ret_sub_entries[entry.SecondIndexRef].append(entry)

    submeshes = {}
    for i, e in enumerate(submesh_entries):
        if e.SecondIndexRef not in submeshes.keys():
            submeshes[e.SecondIndexRef] = []
        submeshes[e.SecondIndexRef].append(all_faces_data[e.SecondIndexRef][int(e.Offset/3):int((e.Offset + e.FacesLength)/3)])

    return submeshes, ret_sub_entries


def get_faces_data(faces_file):
    ref_pkg_name, ref_file, ref_file_type = get_referenced_file(faces_file)
    faces = []
    if ref_file_type == "Faces Header":
        faces_hex = gf.get_hex_data(f'{test_dir}/{ref_pkg_name}/{ref_file}.bin')
        int_faces_data = [int(gf.get_flipped_hex(faces_hex[i:i+4], 4), 16)+1 for i in range(0, len(faces_hex), 4)]
        for i in range(0, len(int_faces_data), 3):
            face = []
            for j in range(3):
                face.append(int_faces_data[i+j])
            faces.append(face)
        return faces
    else:
        print(f'Faces: Incorrect type of file {ref_file_type} for ref file {ref_file} verts file {faces_file}')
        return None


def get_float16(hex_data, j, is_uv=False):
    flt = get_signed_int(gf.get_flipped_hex(hex_data[j * 4:j * 4 + 4], 4), 16)
    if j == 1 and is_uv:
        flt *= -1
    flt = (1 + flt / (2 ** 15 - 1)) * 2 ** (-1)
    return flt


def get_signed_int(hexstr, bits):
    value = int(hexstr, 16)
    if value & (1 << (bits-1)):
        value -= 1 << bits
    return value


def get_verts_data(verts_file):
    """
    Stride length 48 is a dynamic and physics-enabled object.
    """
    # TODO deal with this
    pkg_name = verts_file.pkg_name
    if not pkg_name:
        return None
    # ref_file = f"{all_file_info[verts_file.name]['RefPKG'][2:]}-{all_file_info[verts_file.name]['RefID'][2:]}"
    # ref_pkg_name = gf.get_pkg_name(ref_file)
    # ref_file_type = all_file_info[ref_file]['FileType']
    ref_pkg_name, ref_file, ref_file_type = get_referenced_file(verts_file)
    if ref_file_type == "Stride Header":
        stride_header = verts_file.header

        stride_hex = gf.get_hex_data(f'{test_dir}/{ref_pkg_name}/{ref_file}.bin')

        # print(stride_header.StrideLength)
        hex_data_split = [stride_hex[i:i + stride_header.StrideLength * 2] for i in
                          range(0, len(stride_hex), stride_header.StrideLength * 2)]
    else:
        print(f'Verts: Incorrect type of file {ref_file_type} for ref file {ref_file} verts file {verts_file}')
        return None
    # print(verts_file.name)

    if stride_header.StrideLength == 4:
        """
        UV info for dynamic, physics-based objects.
        """
        coords = get_coords_4(hex_data_split)
    elif stride_header.StrideLength == 8:
        """
        Coord info for static and dynamic, non-physics objects.
        ? info for dynamic, physics-based objects.
        """
        coords = get_coords_8(hex_data_split)
    elif stride_header.StrideLength == 12:
        """
        Coord info takes up same 8 stride, also 2 extra bits.
        """
        # TODO ADD PROPER SUPPORT
        coords = get_coords_8(hex_data_split)
    elif stride_header.StrideLength == 16:
        """
        """
        coords = get_coords_16(hex_data_split)
    elif stride_header.StrideLength == 20:
        """
        UV info for static and dynamic, non-physics objects.
        """
        coords = get_coords_20(hex_data_split)
    elif stride_header.StrideLength == 24:
        """
        UV info for dynamic, non-physics objects gear?
        """
        coords = get_coords_24(hex_data_split)
    elif stride_header.StrideLength == 28:
        """
        Coord info takes up same 8 stride, idk about other stuff
        """
        # TODO ADD PROPER SUPPORT
        coords = get_coords_8(hex_data_split)
    elif stride_header.StrideLength == 32:
        """
        Coord info takes up same 8 stride, idk about other stuff
        """
        # TODO ADD PROPER SUPPORT
        coords = get_coords_8(hex_data_split)
    elif stride_header.StrideLength == 48:
        """
        Coord info for dynamic, physics-based objects.
        """
        # print('Stride 48')
        coords = get_coords_48(hex_data_split)
    else:
        print(f'Need to add support for stride length {stride_header.StrideLength}, file is {verts_file.name} ref {ref_file}')
        quit()

    return coords


def get_coords_4(hex_data_split):
    coords = []
    for hex_data in hex_data_split:
        coord = []
        for j in range(2):
            flt = get_float16(hex_data, j, is_uv=True)
            coord.append(flt)
        coords.append(coord)
    return coords


def get_coords_8(hex_data_split):
    coords = []
    for hex_data in hex_data_split:
        coord = []
        # magic, magic_negative = get_float16(hex_data[12:16], 0)
        for j in range(3):
            flt = get_float16(hex_data, j, is_uv=False)
            coord.append(flt)
        coords.append(coord)
    return coords


def get_coords_16(hex_data_split):
    coords = []
    for hex_data in hex_data_split:
        coord = []
        # magic, magic_negative = get_float16(hex_data[12:16], 0)
        for j in range(2):
            flt = get_float16(hex_data, j, is_uv=False)
            coord.append(flt)
        coords.append(coord)
    return coords


def get_coords_20(hex_data_split):
    coords = []
    for hex_data in hex_data_split:
        coord = []
        for j in range(2):
            flt = get_float16(hex_data, j, is_uv=True)
            coord.append(flt)
        coords.append(coord)
    return coords


def get_coords_24(hex_data_split):
    coords = []
    for hex_data in hex_data_split:
        coord = []
        for j in range(2):
            flt = get_float16(hex_data, j, is_uv=True)
            coord.append(flt)
        coords.append(coord)
    return coords


def get_coords_48(hex_data_split):
    coords = []
    for hex_data in hex_data_split:
        coord = []
        for j in range(3):
            flt = struct.unpack('f', bytes.fromhex(hex_data[j * 8:j * 8 + 8]))[0]
            coord.append(flt)
        coords.append(coord)
    return coords



def trim_verts_data(verts_data, faces_data):
    all_v = []
    for face in faces_data:
        for v in face:
            all_v.append(v)
    return verts_data[min(all_v)-1:max(all_v)]


def get_obj_str(faces_data, verts_data):
    vns = []
    vts = []
    verts_str = ''
    for coord in verts_data:
        # if coord[-1] == 0.3535:
        #     coord = [round(x*(1/0.3535), 4) for x in coord]
        verts_str += f'v {coord[0]} {coord[1]} {coord[2]}\n'
        # print(coord)
        if len(coord) > 3:
            vts.append(coord[3:6])
            vns.append(coord[6:9])
            # vts.append(coord)
            # vns.append(coord)
    for coord in vts:
        if coord:
            verts_str += f'vt {coord[0]} {coord[1]}\n'
        # verts_str += f'vt {coord[3:]}\n'
        # verts_str += f'vt \n'
    for coord in vns:
        if coord:
            verts_str += f'vn {coord[0]} {coord[1]} {coord[2]}\n'
        # print(coord)
        # print(np.sqrt(coord[5][0]**2 + coord[6][0]**2 + coord[7][0]**2))
        # verts_str += f'vn {coord[3:]}\n'
    faces_str = ''
    for face in faces_data:
        faces_str += f'f {face[0]}/{face[0]}/{face[0]} {face[1]}/{face[1]}/{face[1]} {face[2]}/{face[2]}/{face[2]}\n'
    return verts_str + faces_str  # for sep remove , replace with +


def write_fbx(faces_data, verts_data, name):
    controlpoints = [fbx.FbxVector4(x[0], x[1], x[2]) for x in verts_data]
    # manager = Manager()
    # manager.create_scene(name)
    fb = pfb.FBox()
    fb.create_node()

    mesh = fbx.FbxMesh.Create(fb.scene, name)

    # for vert in verts_data:
        # fb.create_mesh_controlpoint(vert[0], vert[1], vert[2])
    controlpoint_count = len(controlpoints)
    mesh.InitControlPoints(controlpoint_count)
    for i, p in enumerate(controlpoints):
        mesh.SetControlPointAt(p, i)
    for face in faces_data:
        mesh.BeginPolygon()
        mesh.AddPolygon(face[0]-1)
        mesh.AddPolygon(face[1]-1)
        mesh.AddPolygon(face[2]-1)
        mesh.EndPolygon()

    node = fbx.FbxNode.Create(fb.scene, '')
    node.SetNodeAttribute(mesh)
    fb.scene.GetRootNode().AddChild(node)
    try:
        os.mkdir(f'C:/d2_model_temp/texture_models/{name[:8]}/')
    except:
        pass
    fb.export(save_path=f'C:/d2_model_temp/texture_models/{name[:8]}/{name}.fbx')


def write_obj(obj_strings, hsh):
    try:
        os.mkdir(f'C:/d2_model_temp/texture_models/{hsh[:8]}/')
    except FileExistsError:
        pass
    with open(f'C:/d2_model_temp/texture_models/{hsh[:8]}/{hsh}.obj', 'w') as f:
        for string in obj_strings:
            f.write(string)
    print('Written to file.')


if __name__ == '__main__':
    """
    To redesign:
    - add the second index stuff
    - remove the weird iteration system for now for finding verts
    - read entries from the data file
    - mess around until you find the answer
    """
    # CCC7F380
    # E73AED80
    # 86BFFE80
    # 0A34ED80
    get_model('86BFFE80')
