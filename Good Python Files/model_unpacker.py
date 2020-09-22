import struct
import pkg_db
from dataclasses import dataclass, fields
import numpy as np
import binascii
import os
# import pyfbx
import fbx
import pyfbx_jo as pfb

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


def fill_hex_with_zeros(s, desired_length):
    return ("0"*desired_length + s)[-desired_length:]


def get_hex_data(direc):
    t = open(direc, 'rb')
    h = t.read().hex().upper()
    return h


def get_flipped_hex(h, length):
    if length % 2 != 0:
        print("Flipped hex length is not even.")
        return None
    return "".join(reversed([h[:length][i:i + 2] for i in range(0, length, 2)]))


def get_file_from_hash(hsh):
    first_int = int(hsh.upper(), 16)
    one = first_int - 2155872256
    first_hex = hex(int(np.floor(one/8192)))
    second_hex = hex(first_int % 8192)
    return f'{fill_hex_with_zeros(first_hex[2:], 4)}-{fill_hex_with_zeros(second_hex[2:], 4)}'.upper()


def get_hash_from_file(file):
    pkg = file.replace(".bin", "").upper()

    firsthex_int = int(pkg[:4], 16)
    secondhex_int = int(pkg[5:], 16)

    one = firsthex_int*8192
    two = hex(one + secondhex_int + 2155872256)
    return two[2:]


def get_header(file_hex, header):
    # The header data is 0x16F bytes long, so we need to x2 as python reads each nibble not each byte

    for f in fields(header):
        if f.type == np.uint32:
            flipped = "".join(get_flipped_hex(file_hex, 8))
            value = np.uint32(int(flipped, 16))
            setattr(header, f.name, value)
            file_hex = file_hex[8:]
        elif f.type == np.uint16:
            flipped = "".join(get_flipped_hex(file_hex, 4))
            value = np.uint16(int(flipped, 16))
            setattr(header, f.name, value)
            file_hex = file_hex[4:]
    return header


test_dir = 'C:/d2_output/'


def get_pkg_name(file):
    if not file:
        print(f'{file} is invalid.')
        return None
    pkg_id = file.split('-')[0]
    for folder in os.listdir(test_dir):
        if pkg_id.lower() in folder.lower():
            pkg_name = folder
            break
    else:
        print(f'Could not find folder for {file}. File is likely not a model or folder does not exist.')
        return None
    return pkg_name


def get_referenced_file(file):
    pkg_name = get_pkg_name(file)
    if not pkg_name:
        return None, None, None
    entries_refpkg = {x: y for x, y in pkg_db.get_entries_from_table(pkg_name, 'FileName, RefPKG')}
    entries_refid = {x: y for x, y in pkg_db.get_entries_from_table(pkg_name, 'FileName, RefID')}
    if file not in entries_refpkg.keys():
        return None, None, None
    ref_pkg_id = entries_refpkg[file][2:]
    ref_pkg_name = get_pkg_name(f'{ref_pkg_id}-')
    if not ref_pkg_name:
        return None, None, None
    entries_filetype = {x: y for x, y in pkg_db.get_entries_from_table(ref_pkg_name, 'FileName, FileType')}

    ref_file_name = f'{ref_pkg_id}-' + entries_refid[file][2:]
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
    model_file = get_file_from_hash(get_flipped_hex(model_file_hash, 8))
    model_data_file = get_model_data_file(model_file)
    all_file_info = {x[0]: dict(zip(['RefID', 'RefPKG', 'FileType'], x[1:])) for x in
                     pkg_db.get_entries_from_table('Everything', 'FileName, RefID, RefPKG, FileType')}
    submeshes_verts, submeshes_faces = get_verts_faces_data(model_data_file, all_file_info)
    obj_strings = []
    max_vert_used = 0
    # all_verts_str = ''  # joined obj
    # all_faces_str = ''  # joined obj
    for index_2 in range(len(submeshes_verts.keys())):
        for index_3 in range(len(submeshes_verts[index_2])):
            adjusted_faces_data, max_vert_used = adjust_faces_data(submeshes_faces[index_2][index_3], max_vert_used)
            obj_str = get_obj_str(adjusted_faces_data, submeshes_verts[index_2][index_3])  # replace with obj_str = for separated obj, otherwise verts_str, faces_str = for joined obj
            obj_str += f'o {model_file_hash}_0_{index_2}_{index_3}\n'  # separated obj
            obj_strings.append(obj_str)  # separated obj
            # all_verts_str += verts_str  # joined obj
            # all_faces_str += faces_str  # joined obj
            write_fbx(adjusted_faces_data, submeshes_verts[index_2][index_3], model_file_hash, f'{model_file_hash}_0_{index_2}_{index_3}')

    # obj_strings = f'o {model_file_hash}\n' + all_verts_str + all_faces_str  # joined obj
    write_obj(obj_strings, model_file_hash)



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


def get_verts_faces_data(model_data_file, all_file_info):
    all_faces_data = []
    all_verts_8_data = []
    all_verts_20_data = []
    # pkg_db.start_db_connection(version)
    faces_files, verts_8_files, verts_20_files, model_data_hex = get_faces_verts_files(model_data_file)
    if not faces_files or not verts_8_files or not verts_20_files:
        return None, None
    for i, faces_file in enumerate(faces_files):
        verts_8_file = verts_8_files[i]
        verts_20_file = verts_20_files[i]
        faces_data = get_faces_data(faces_file, all_file_info)
        if not verts_8_file:
            return None, None
        verts_8_data = get_verts_data(verts_8_file, all_file_info, b_20=False)
        # Even though this may be None it should be okay.
        verts_20_data = get_verts_data(verts_20_file, all_file_info, b_20=True)
        if not verts_8_data or verts_8_data == []:
            return None, None
        if not faces_data or faces_data == []:
            return None, None
        all_faces_data.append(faces_data)
        all_verts_8_data.append(verts_8_data)
        all_verts_20_data.append(verts_20_data)
    submeshes_faces, submeshes_entries = separate_submeshes_remove_lods(model_data_hex, all_faces_data)
    submeshes_verts = {x: [] for x in submeshes_faces.keys()}
    for i in submeshes_faces.keys():
        for j, faces in enumerate(submeshes_faces[i]):
            if submeshes_entries[i][j].EntryType == 769:
                submeshes_verts[i].append(trim_verts_data(all_verts_8_data[i], faces))
            elif submeshes_entries[i][j].EntryType == 770:
                # TODO currently only thing that doesn't work. Literally everything else does.
                submeshes_verts[i].append(trim_verts_data(all_verts_8_data[i], faces))

    return submeshes_verts, submeshes_faces


def get_model_data_file(model_file):
    pkg_name = get_pkg_name(model_file)
    if not pkg_name:
        return None
    model_hex = get_hex_data(f'{test_dir}/{pkg_name}/{model_file}.bin')
    model_data_hash = get_flipped_hex(model_hex[16:24], 8)
    return get_file_from_hash(model_data_hash)


def get_faces_verts_files(model_data_file):
    faces_files = []
    verts_8_files = []
    verts_20_files = []
    pkg_name = get_pkg_name(model_data_file)
    if not pkg_name:
        return None, None, None, None
    try:
        model_data_hex = get_hex_data(f'{test_dir}/{pkg_name}/{model_data_file}.bin')
    except FileNotFoundError:
        print(f'No folder found for file {model_data_file}. Likely need to unpack it or design versioning system.')
        return None, None, None, None
    split_hex = model_data_hex.split('BD9F8080')[-1]
    model_count = int(get_flipped_hex(split_hex[:4], 4), 16)
    relevant_hex = split_hex[32:]
    for i in range(model_count):
        faces_hash = get_flipped_hex(relevant_hex[32*i:32*i+8], 8)
        verts_8_hash = get_flipped_hex(relevant_hex[32*i+8:32*i+16], 8)
        verts_20_hash = get_flipped_hex(relevant_hex[32*i+16:32*i+24], 8)
        if faces_hash == '' or verts_8_hash == '' or verts_20_hash == '':
            return None, None, None, None
        faces_file, verts_8_file, verts_20_file = get_file_from_hash(faces_hash), get_file_from_hash(verts_8_hash), get_file_from_hash(verts_20_hash)
        faces_files.append(faces_file)
        verts_8_files.append(verts_8_file)
        verts_20_files.append(verts_20_file)

    return faces_files, verts_8_files, verts_20_files, model_data_hex


def separate_submeshes_remove_lods(model_data_hex, all_faces_data):
    """
    If entry is a submesh, I believe the range is just from Offset to Offset + FacesLength, where FacesLength/3 is the number of final faces
    If entry is LOD, range is the same where FacesLength/3 is the number of removed faces.
    Hence, we can pull all the stuff we want out by just separating [Offset:Offset + FacesLength]
    """
    unk_entries_count = int(get_flipped_hex(model_data_hex[80*2:80*2 + 8], 4), 16)
    unk_entries_offset = 96

    end_offset = unk_entries_offset + unk_entries_count * 8
    end_place = int(model_data_hex[end_offset*2:].find('BD9F8080')/2)
    useful_entries_count = int(get_flipped_hex(model_data_hex[(end_offset + end_place + 4)*2:(end_offset + end_place + 6)*2], 4), 16)
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
        print()

    return submeshes, ret_sub_entries


def get_faces_data(faces_file, all_file_info):
    ref_file = f"{all_file_info[faces_file]['RefPKG'][2:]}-{all_file_info[faces_file]['RefID'][2:]}"
    ref_pkg_name = get_pkg_name(ref_file)
    ref_file_type = all_file_info[ref_file]['FileType']
    # ref_pkg_name, ref_file, ref_file_type = get_referenced_file(faces_file)
    faces = []
    if ref_file_type == "Faces Header":
        faces_hex = get_hex_data(f'{test_dir}/{ref_pkg_name}/{ref_file}.bin')
        int_faces_data = [int(get_flipped_hex(faces_hex[i:i+4], 4), 16)+1 for i in range(0, len(faces_hex), 4)]
        for i in range(0, len(int_faces_data), 3):
            face = []
            for j in range(3):
                face.append(int_faces_data[i+j])
            faces.append(face)
        return faces
    else:
        print(f'Faces: Incorrect type of file {ref_file_type} for ref file {ref_file} verts file {faces_file}')
        return None


def get_verts_data(verts_file, all_file_info, b_20):
    # TODO deal with this
    pkg_name = get_pkg_name(verts_file)
    if not pkg_name:
        return None
    ref_file = f"{all_file_info[verts_file]['RefPKG'][2:]}-{all_file_info[verts_file]['RefID'][2:]}"
    ref_pkg_name = get_pkg_name(ref_file)
    ref_file_type = all_file_info[ref_file]['FileType']
    # ref_pkg_name, ref_file, ref_file_type = get_referenced_file(verts_file)
    if ref_file_type == "Stride Header":
        header_hex = get_hex_data(f'{test_dir}/{pkg_name}/{verts_file}.bin')
        stride_header = get_header(header_hex, Stride12Header())

        stride_hex = get_hex_data(f'{test_dir}/{ref_pkg_name}/{ref_file}.bin')

        hex_data_split = [stride_hex[i:i + stride_header.StrideLength * 2] for i in
                          range(0, len(stride_hex), stride_header.StrideLength * 2)]
    else:
        print(f'Verts: Incorrect type of file {ref_file_type} for ref file {ref_file} verts file {verts_file}')
        return None

    coords = []
    for hex_data in hex_data_split:
        if b_20:
            hex_data = hex_data[:12]
        coord = []
        for j in range(3):
            selection = get_flipped_hex(hex_data[j * 4:j * 4 + 4], 4)
            exp_bitdepth = 0
            mantissa_bitdepth = 15
            bias = 2 ** (exp_bitdepth - 1) - 1
            mantissa_division = 2 ** mantissa_bitdepth
            int_fs = int(selection, 16)
            mantissa = int_fs & 2 ** mantissa_bitdepth - 1
            mantissa_abs = mantissa / mantissa_division
            exponent = (int_fs >> mantissa_bitdepth) & 2 ** exp_bitdepth - 1
            negative = int_fs >> 15
            if exponent == 0:
                flt = mantissa_abs * 2 ** (bias - 1)
            else:
                print('Incorrect file given.')
                return
            if negative:
                flt += -0.35
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
    verts_str = ''
    for coord in verts_data:
        verts_str += f'v {coord[0]} {coord[1]} {coord[2]}\n'
    faces_str = ''
    for face in faces_data:
        faces_str += f'f {face[0]}// {face[1]}// {face[2]}//\n'
    return verts_str + faces_str  # for sep remove , replace with +


def write_fbx(faces_data, verts_data, folder_name, name):
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

    fb.export(save_path=f'C:/d2_model_temp/texture_models/{name}.fbx')


def write_obj(obj_strings, hsh):
    with open(f'C:/d2_model_temp/texture_models/{hsh}.obj', 'w') as f:
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
    #7C23ED80
    get_model('B901C780')
