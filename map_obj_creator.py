import os
import pkg_db
import struct
from dataclasses import dataclass, fields, field
from typing import List
import numpy as np
pkgs_dir = 'D:/D2_Datamining/Package Unpacker/2_9_0_1/output_all/'

# package_dir_list = ['eden_06a1',
#                     'eden_06a2',
#                     'eden_036a']  # With / at end

package_dir_list = ['cayde_6_feet_under_0368']


@dataclass
class MapHeader:
    Identifier: np.uint32 = np.uint32(0)  # 0; should equal D6000012
    Unknown: List[np.uint8] = field(default_factory=list)  # [0x40] padding from 0x04->0x43
    SecondDataStart: np.uint32 = np.uint32(0) # 0x44
    Field48: np.uint32 = np.uint32(0)
    SecondDataEnd: np.uint32 = np.uint32(0) # 0x4C
    Field50: np.uint32 = np.uint32(0)  # padding
    Field54: np.uint32 = np.uint32(0)
    Field58: np.uint32 = np.uint32(0)
    Field5C: np.uint32 = np.uint32(0)
    Field60: np.uint32 = np.uint32(0)
    Field64: np.uint32 = np.uint32(0)
    Field68: np.uint32 = np.uint32(0)
    Field6C: np.uint32 = np.uint32(0)
    FirstDataStart: np.uint32 = np.uint32(0)  # 70
    Field74: np.uint32 = np.uint32(0)
    FirstDataEnd: np.uint32 = np.uint32(0)  # 78
    # There's some extra stuff but idk what it does


def get_hex_data(direc):
    t = open(direc, 'rb')
    h = t.read().hex().upper()
    return h


def get_flipped_hex(h, length):
    """
    Flips the hex around so the data is read correctly eg 00 80 00 00 = 00 00 80 00. Takes every pair of bytes and
    flips them so AC 18 = 18 AC.
    :param h: the hex string to flip around
    :param length: how long this hex string is (len(h) doesn't work)
    :return: the flipped hex
    """
    if length % 2 != 0:
        print("Flipped hex length is not even.")
        return None
    return "".join(reversed([h[:length][i:i + 2] for i in range(0, length, 2)]))


def get_header(file_hex):
    header_length = int('0x16F', 16)
    # The header data is 0x16F bytes long, so we need to x2 as python reads each nibble not each byte
    header = file_hex[:header_length * 2]

    map_header = MapHeader()
    for f in fields(map_header):
        if f.type == np.uint32:
            flipped = "".join(get_flipped_hex(header, 8))
            value = np.uint32(int(flipped, 16))
            setattr(map_header, f.name, value)
            header = header[8:]
        elif f.type == List[np.uint8]:
            # print(header)
            # these are 2*0x40 as the arrays need to be 0x40 long and uint8 so 2*0x40 bytes
            flipped = get_flipped_hex(header, 2*0x40)
            # print(flipped)
            value = [np.uint8(int(flipped[i:i + 2], 16)) for i in range(len(flipped))]
            setattr(map_header, f.name, value)
            header = header[2*0x40:]
    return map_header


def file_to_coords(file_hex):
    hex_floats = [file_hex[i:i+8] for i in range(0, len(file_hex), 8)]
    floats = []
    for hex_float in hex_floats:
        # We don't need to worry about flipping hex as this unpack is:
        # 1. Little Endian 2. DCBA (so reverses the direction)
        float_value = struct.unpack('f', bytes.fromhex(hex_float))[0]
        floats.append(str(round(float_value, 2)))
    # Formatting for x,y,z
    coords = [floats[i:i+3] for i in range(0, len(floats), 3)]
    print(len(coords))
    coords = [x for x in coords if len(x) == 3]
    # ban_coord_counter_x = len([x for x in coords if abs(float(x[0])) < 500])
    # ban_coord_counter_y = len([x for x in coords if abs(float(x[1])) < 500])
    # limit = 0.5 * len(coords)
    # print(ban_coord_counter_x, ban_coord_counter_y, limit)
    # if ban_coord_counter_x > limit and ban_coord_counter_y > limit:
    #     return None
    return coords


def clean_coord(coord):
    # if len(coord) != 3:
    #     return None
    for i in coord:
        if abs(float(i)) > 1e6:
            return None
    # if abs(float(coord[0])) < 50:
    #     return None
    return coord


def coords_to_obj(coords, pkg, file_name):
    lines_to_write = []
    #print(f'Number of coords {len(coords)}')
    for coord in coords:
        coord = clean_coord(coord)
        if not coord:
            continue
        line = f'v {coord[0]} {coord[1]} {coord[2]}\n'  # Coords
        if 'nan' not in line:
            # We don't want a coord that just stacks up at (0, 0, 0)
            if line.count("0.0") != 3:
                lines_to_write.append(line)

    with open(f'Objects/{pkg}/{file_name}.obj', 'w') as q:
        q.write(f'o {file_name}\n')
        for line in lines_to_write:
            q.write(line)

    print(f"\nWritten {len(lines_to_write)} points to {file_name}.obj")


pkg_db.start_db_connection('2_9_0_1')
# want_files = ['06A2-00000D8C', '06A2-00000EE4', '06A2-00000EF5', '06A2-000011EC', '06A2-00001312',
#               '06A2-000013BA', '06A2-00001402']
for pkg in package_dir_list:
    try:
        os.mkdir("Objects/")
        os.mkdir("Objects/" + pkg)
    except FileExistsError:
        try:
            os.mkdir("Objects/" + pkg)
        except FileExistsError:
            pass
    entries = {x: y for x, y in pkg_db.get_entries_from_table(pkg, 'FileName, FileType')}

    for file in os.listdir(pkgs_dir + pkg):
        file_name = file.split('.')[0]
        # if file_name not in want_files:
        #     continue
        if entries[file_name] == "Mapping Data":
            file_hex = get_hex_data(pkgs_dir + pkg + '/' + file)
            header = get_header(file_hex)
            if hex(header.Identifier)[2:].upper() != 'D6000012':  # Seems to be required for a "good" file
                continue
            data1 = file_hex[header.FirstDataStart*2:header.FirstDataEnd*2]
            data2 = file_hex[header.SecondDataStart*2:header.SecondDataEnd*2]
            coords = file_to_coords(data1 + data2)
            if not coords:
                print(f"Not converting {file_name} to obj")
                continue
            coords_to_obj(coords, pkg, file_name)


# Could write up different extractors:
# 1. The normal extractor we have now
# 2. An extractor that prefixes with different bytes (eg 44, 3F, 42, 4C, etc to identify which ones are good)