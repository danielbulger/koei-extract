# koei-extract
Script to extract game files from some PS2-era KOEI games

# Archive Format

Each archive made up of two files: 

* The Index File which defines the size and offsets of each file
* Data File is stores the actual file data.

The archive format does not allow for named lookups or error checking through checksums. 

## Index File

    struct IndexFile {
        Header header;
        IndexEntry entries[num_files];
    }

    struct Header {
        uint32 magic;
        uint32 num_files;
        uint32 dummy;
        uint32 zero;
    }

    struct IndexEntry {
        uint32 offset;
        uint32 rounded_size;
        uint32 size;
        uint32 zero;
    }

## Data File

The data files are stored in 0x800 multiples and are padded to align if it does not fall on bounds.

The data files can either be stored as compressed or uncompressed. If the file is compressed the first 4 bytes should be 'LZ2P'.
    
    struct DataFile {
        DataFileEntry entries[num_files];
    }
    
    struct DataFileEntry {
        union {
            UncompressedFileEntry;

            CompressedFileEntry;
        };

        char padding[?];
    }

    struct UncompressedFileEntry {
        char data[size];
    }

    struct CompressedFileEntry {
        uint32 magic; 
        uint32 dummy;
        uint32 decompressed_size;
        uint32 compressed_size;

        char data[compressed_size];
    }

# Decompression Algorithm

A compressed file is broken up into variable length blocks, each headed by a single byte flag. 

The flag defines which operation to perform on the block itself. If no flag is defined in the header, the block is not decompressed and will be written to the decompression buffer as is.

The LZSS decompression dictionary is the current decompression buffer. 
    
    enum Flags {
        LZSS = 0x80,
        RLE = 0x40
    }
    
    struct LZSSBlock {
        uint8 flag;
            
        // Uses the bottom 6 bits from the flag. 
        int8 length: 6;
        // The offset of the decompression buffer where the dictionary is
        unt16 dictionary_offset;
    }
    
    struct RLEBlock {
        uint8 flag : 3;
        // Length is encoded as 11 bits and uses the bottom 3 bits of the flag 
        uint16 length : 8;
        uint8 value;
    }
    
    struct UncompressedBlock {
        // Is the flag, reused as the length of the block
        uint8 length;
        char data[length];
    }

# References

[Run-length Encoding](https://en.wikipedia.org/wiki/Run-length_encoding)

[LZSS](https://en.wikipedia.org/wiki/Lempel%E2%80%93Ziv%E2%80%93Storer%E2%80%93Szymanski)
