import os
import re
import map_unpacker
import model_unpacker

# search_dir = 'M:/D2_Datamining/UNPACKER/D2_Datamining_Expanded/'
search_dir = 'D:/D2_Datamining/Package Unpacker/2_9_0_1/output_all/'
# search_dir = 'C:/d2_output_2_9_1_0/'
search_str = '4EF3FE80'


def get_hex_data(direc):
    t = open(direc, 'rb')
    h = t.read().hex().upper()
    return h


def get_hex_from_pkg():
    main_hex = get_hex_data(f'{search_dir}{folder}/{file}')

    transform_count = int(map_unpacker.get_flipped_hex(main_hex[64*2:64*2+4], 4), 16)
    transform_offset = 192
    transform_length = transform_count*48

    entry_count = int(map_unpacker.get_flipped_hex(main_hex[88*2:88*2+4], 4), 16)
    model_offset = transform_offset + transform_length + 32
    model_length = entry_count * 4
    model_refs_hex = main_hex[model_offset*2:model_offset*2 + model_length*2]

    copy_offset = model_offset + model_length + int(main_hex[model_offset*2+model_length*2:].find('90718080')/2) + 8
    copy_count_hex = main_hex[copy_offset*2:]

    return model_refs_hex, copy_count_hex


def get_copies():
    model_refs_hex, copy_count_hex = get_hex_from_pkg()
    model_refs = map_unpacker.get_model_refs(model_refs_hex)
    copy_counts = map_unpacker.get_copy_counts(copy_count_hex)
    dic = dict(zip(model_refs, copy_counts))
    print('Number of copies in file:', dic[search_str])
    return dic[search_str
    ]

banned_folders = [
    'img',
    'activities',
    'environments',
    # 'sandbox',
    'globals',
    'investment',
    'shared',
    'ui',
    'audio'
]

if __name__ == '__main__':
    wishes_found = 0
    for i, folder in enumerate(os.listdir(search_dir)):
        banned = False
        for bf in banned_folders:
            if bf in folder:
                banned = True
        if banned:
            continue

        # if i < 17:
        #     continue
        # wishes_found = 10

        if 'sandbox_03f7' not in folder:
            continue

        print(f'Searching in {folder}, index {i}')
        for file in os.listdir(search_dir + folder):
            # print(file)
            if file == 'img':
                continue
            file_hex = get_hex_data(search_dir + folder + '/' + file)
            # find = [m.start() for m in re.finditer(search_str, file_hex)]
            find = file_hex.find(search_str)
            if find and find != -1:
                print(f'Found string in {file} at bytes {find}.')  # There may be more as not accounting for copies.
                # copies = get_copies()
                # wishes_found += copies
                # print('Wishes found total:', wishes_found)
            # if file == '036D-00000256.bin':
            #     print()