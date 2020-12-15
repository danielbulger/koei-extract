import os
import struct
from argparse import ArgumentParser
from typing import List, Dict

game_config = {
    'orochi': {
        'magic': 1397568588,
        'index_endian': '>I',
        'entry_endian': '<I',
        'index_file_suffix': '.IDX',
        'data_file_suffix': '.LNK',
        'files': [
            'LINKDATA_ENS'
        ]
    },
    'dw5': {
        'magic': 1278496083,
        'index_endian': '<I',
        'entry_endian': '<I',
        'index_file_suffix': '.IDX',
        'data_file_suffix': '.BIN',
        'files': [
            'LINKBGM',
            'LINKDATA',
            'LINKMOV',
            'LINKSE'
        ]
    }
}


class FileIndex:

    def __init__(self, offset, size):
        self.offset = offset
        self.size = size

    def __str__(self):
        return f'offset: {self.offset}, size: {self.size}'

    def __repr__(self):
        return str(self)


def read_index(config: Dict, input_file) -> List[FileIndex]:
    indexes = []
    with open(input_file, 'rb') as index_file:

        header = index_file.read(16)

        magic, num_files, dummy, zero = [x[0] for x in struct.iter_unpack(config['index_endian'], header)]

        if magic != config['magic']:
            raise Exception(f'Invalid magic {magic}')

        if zero != 0:
            raise Exception(f'Invalid header expected zero got {zero}')

        for x in range(num_files):
            file_index = index_file.read(16)

            """
            All file entries are aligned to a 0x800 multiple
            offset stores the multiple of 2048 so the real offset is 0x800 * offset
            
            block_size is the size of the file rounded to the next highest 2048 multiple
            
            Depending on the game size is the real physical size of the file or the 
            transformed multiple of 2048
            
            zero is zero.
            """
            offset, block_size, size, zero = [x[0] for x in struct.iter_unpack(config['index_endian'], file_index)]

            if zero != 0:
                raise Exception(f"Invalid archive entry for {input_file} entry: {x}")

            indexes.append(FileIndex(offset * 0x800, size))

        return indexes


def is_compressed(file_data) -> bool:
    return file_data[:4] == b'LZP2'


def decompress(config, file_id, file_data) -> bytearray:
    header_size = 0x10

    header, dummy, decompressed, compressed = [x[0] for x in struct.iter_unpack(config['entry_endian'], file_data[:header_size])]

    next_flag = file_data[header_size]
    rd_index = header_size + 1

    output = bytearray()

    while True:

        flag = next_flag
        block_index = rd_index

        if next_flag == 0:
            break

        if next_flag & 0x80 != 0:
            # LZSS

            length = ((flag & 0x78) >> 3) + 3
            offset = len(output) - (((flag & 7) << 8 | file_data[block_index]) + 1)
            block_index = rd_index + 1

            for _ in range(length):
                output.append(output[offset])
                offset += 1

        elif next_flag & 0x40 != 0:
            # RELU

            value = file_data[block_index + 1]
            length = ((flag & 0x3F) * 0x100 + file_data[block_index]) + 4
            block_index = rd_index + 2

            for x in range(length):
                output.append(value)

        else:
            # Uncompressed, the block size is the flag.
            for _ in range(flag):
                output.append(file_data[block_index])
                block_index += 1

        next_flag = file_data[block_index]
        rd_index = block_index + 1

    if len(output) != decompressed:
        raise Exception(f"Invalid decompression {file_id}: expected {decompressed} got {len(output)}")

    return output


def extract_files(config, file_indexes: List[FileIndex], data_file_path: str, extract_dir: str):

    # Make the extract directory if they don't already exist
    if not os.path.isdir(extract_dir):
        os.makedirs(extract_dir, exist_ok=True)

    with open(data_file_path, 'rb') as data_file:
        for file_id, index in enumerate(file_indexes):

            data_file.seek(index.offset)

            file_data = data_file.read(index.size)

            compressed = is_compressed(file_data)

            if compressed:
                file_data = decompress(config, file_id, file_data)

            extract_path = os.path.join(extract_dir, f'{file_id}.bin')
            with open(extract_path, 'wb+') as output_file:
                output_file.write(file_data)

            print(f'\tExtracted {file_id}: compressed={compressed}')


def parse_args():
    parser = ArgumentParser()

    parser.add_argument('--game', help='The game to extract from')
    parser.add_argument("--install-dir", help="Install directory containing the data files")
    parser.add_argument("--extract-dir", help="Extract directory")

    return parser.parse_args()


def main():
    args = parse_args()

    if args.game not in game_config:
        raise Exception(f'Unknown game {args.game}')

    config = game_config[args.game]

    for file in config['files']:

        print(f'Starting archive {file}')

        base_path = os.path.join(args.install_dir, file)

        indexes = read_index(config, base_path + config['index_file_suffix'])

        extract_path = os.path.join(args.extract_dir, file)

        extract_files(config, indexes, base_path + config['data_file_suffix'], extract_path)


if __name__ == '__main__':
    main()
