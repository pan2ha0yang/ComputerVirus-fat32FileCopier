import filecmp
import sys


def ReadBPB(DriveLetter: str):
    disk = open(r'\\.\\' + DriveLetter, 'rb')
    JmpCmd = disk.read(3)
    if JmpCmd[0] == 235 and JmpCmd[1] == 88 and JmpCmd[2] == 144:
        disk.seek(0)
        # 读取DBR中BPB首字段“每扇区字节数”
        disk.read(0xb)
        SectorSize = int.from_bytes(disk.read(2), 'little')
        # 读取BPB中“每簇扇区数”
        disk.seek(0xd)
        numSectorsPerCluster = int.from_bytes(disk.read(1), 'little')
        # 读取BPB中“保留扇区数”
        disk.seek(0xe)
        numReservedSectors = int.from_bytes(disk.read(2), 'little')
        # 读取BPB中“FAT的个数”
        disk.seek(0x10)
        numFAT = int.from_bytes(disk.read(1), 'little')
        # 读取BPB中“本分区占用的扇区数”
        disk.seek(0x20)
        numSectorsInPartition = int.from_bytes(disk.read(4), 'little')
        # 读取BPB中“每个FAT占用的扇区数”
        disk.seek(0x24)
        numSectorsPerFAT = int.from_bytes(disk.read(4), 'little')
        # 读取BPB中“根目录首簇号”
        disk.seek(0x2c)
        BPBRootClus = int.from_bytes(disk.read(4), 'little')
        disk.close()

        return SectorSize, numSectorsPerCluster, numReservedSectors, numFAT, \
               numSectorsInPartition, numSectorsPerFAT, BPBRootClus
    else:
        disk.close()
        print("ERROR:Not DBR!")
        return False


def ReadShortDirectoryEntry(StartByte: int, DriveLetter: str):
    # 读取一个短目录项单元
    disk = open(r'\\.\\' + DriveLetter, 'rb')
    disk.read(StartByte)
    ShortEntry = disk.read(32)
    disk.close()
    # 检查该目录项是否被删除
    # flag = hex(ShortEntry[0])
    # if flag == "0xe5":
    #     print("ERROR:This Short Directory Entry Has Been Deleted!")
    #     return False
    # 获取文件名
    FileName = ShortEntry[0:8]
    BytesList = []
    for i in range(0, 8):
        BytesList.append(chr(FileName[i]))
    FileName = ''.join(BytesList)
    # 获取扩展名
    Extension = ShortEntry[8:11]
    BytesList = []
    for i in range(0, 3):
        BytesList.append(chr(Extension[i]))
    Extension = ''.join(BytesList)
    # 获取属性
    Attribute = ShortEntry[11]
    if Attribute == int(0x01):
        Attribute = "read only"
    elif Attribute == int(0x02):
        Attribute = "hidden"
    elif Attribute == int(0x04):
        Attribute = "system"
    elif Attribute == int(0x08):
        Attribute = "volume label"
    elif Attribute == int(0x10):
        Attribute = "directory"
    elif Attribute == int(0x20):
        Attribute = "archive"
    # elif Attribute == int(0x0f):
    #     print("ERROR:This Is A Long Directory Entry!")
    #     return False
    else:
        Attribute = "unknown"
    # 获取起始簇号
    FirstClus = int.from_bytes(ShortEntry[20:22], 'little') * 65536 + int.from_bytes(ShortEntry[26:28], 'little')
    # 获取文件长度
    FileSize = int.from_bytes(ShortEntry[28:32], 'little')

    return ShortEntry, FileName, Extension, Attribute, FirstClus, FileSize


def GetClusChain(SectSize: int, NumReservedSects: int, NumSectsPerFAT: int, FirstClus: int, DriveLetter: str):
    # 读取FAT1
    disk = open(r'\\.\\' + DriveLetter, 'rb')
    disk.read(SectSize * NumReservedSects)
    FAT1 = disk.read(SectSize * NumSectsPerFAT)
    disk.close()
    # 循环获取文件簇链
    ClusChain = [str(FirstClus)]
    Clus = FirstClus
    while 1 < Clus < (SectSize * NumSectsPerFAT) / 4:
        if Clus == int.from_bytes(b'\xff\xff\xff\x0f', 'little'):
            break
        Clus = int.from_bytes(FAT1[(4 * Clus):(4 * Clus + 4)], 'little')
        ClusChain.append(str(Clus))

    return ClusChain[0:-1]


if __name__ == '__main__':
    # 请以"x:\\xxx.xxx"格式输入目标文件路径(英文)
    # 请确保逻辑盘x采用的是FAT32格式
    # 请确保目标文件存在以"."分隔的扩展名
    # 目前仅支持目标文件存放于根目录的情况
    # 若其存放于目录结构中，则需要根据目录的目录项信息及其文件簇的内容执行递归查找，由于时间限制不予实现
    file_path = "h:\\panzhaoyang.docx"
    drive_letter = file_path.split('\\')[0]
    file_whole_name = file_path.split('\\')[-1]
    file_src_ext = file_whole_name.split('.')[-1]
    file_src_name = file_whole_name[0:-(len(file_src_ext)+1)]
    if len(file_src_name) > 8 or len(file_src_ext) > 3:
        print(file_whole_name + " Is A Long-name File")
        if len(file_src_name) > 6:  # 对于存在两个以上的同名文件，即“~n”，这里不考虑
            file_target_name = (file_src_name[0:6] + "~1").upper()
        else:
            file_target_name = (file_src_name + "~1" + " " * (6 - len(file_src_name))).upper()
        if len(file_src_ext) > 3:
            file_target_ext = (file_src_ext[0:3]).upper()
        else:
            file_target_ext = (file_src_ext + " " * (3 - len(file_src_ext))).upper()
    else:
        file_target_name = (file_src_name + " " * (8 - len(file_src_name))).upper()
        file_target_ext = (file_src_ext + " " * (3 - len(file_src_ext))).upper()

    # 计算BPB重要字段
    sector_size, num_sectors_per_cluster, num_reserved_sectors, num_FAT, \
        num_sectors_in_partition, num_sectors_per_FAT, BPB_RootClus = ReadBPB(drive_letter)
    # print("Sector Size:" + str(sector_size))
    # print("The Number Of Sectors Per Cluster:" + str(num_sectors_per_cluster))
    # print("The Number Of Reserved Sectors:" + str(num_reserved_sectors))
    # print("The Number Of FAT:" + str(num_FAT))
    # print("The Number Of Sectors Occupied By This Partition:" + str(num_sectors_in_partition))
    # print("The Number Of Sectors Per FAT:" + str(num_sectors_per_FAT))
    # print("The First Cluster Of Root Directory:" + str(BPB_RootClus))

    # 计算根目录起始扇区号
    first_sector_of_cluster = ((BPB_RootClus - 2) * num_sectors_per_cluster) + \
        num_reserved_sectors + (num_FAT * num_sectors_per_FAT)
    # print("The First Sector Of Root Directory:" + str(first_sector_of_cluster))

    # 计算短文件名目录项
    max_num_entry_root = (sector_size * num_sectors_per_cluster) / 32
    for i in range(0, int(max_num_entry_root)):
        short_entry, file_name, file_ext, file_attr, file_first_clus, file_size = \
            ReadShortDirectoryEntry(first_sector_of_cluster * sector_size + 32 * i, drive_letter)
        if file_target_name == file_name and file_target_ext == file_ext:
            break
    if i == int(max_num_entry_root)-1 and file_target_name != file_name:
        print("Could Not Find Such File!")
        sys.exit()
    print("File Name:" + file_name)
    print("File Extension:" + file_ext)
    print("File Attribute:" + file_attr)
    print("File First Cluster:" + str(file_first_clus))
    print("File Size:" + str(file_size))

    # 计算文件簇链
    file_clus_chain = GetClusChain(sector_size, num_reserved_sectors, num_sectors_per_FAT, file_first_clus,
                                drive_letter)
    print("File Clusters:" + str(file_clus_chain))

    # 复制文件
    file_end_size = file_size % (sector_size * num_sectors_per_cluster)
    if file_end_size == 0:
        file_end_size = sector_size * num_sectors_per_cluster

    disk = open(r'\\.\\' + drive_letter, 'rb')
    file = b''
    for clus in file_clus_chain:
        disk.seek(sector_size * num_reserved_sectors + sector_size * num_sectors_per_FAT * num_FAT + \
                  (int(clus) - 2) * sector_size * num_sectors_per_cluster)
        if clus != file_clus_chain[-1]:
            tmp_file = disk.read(sector_size * num_sectors_per_cluster)
        else:
            tmp_file = disk.read(file_end_size)
        file = file + tmp_file
    disk.close()

    copy = open(drive_letter + '\\copy', 'wb')
    copy.write(file)
    copy.close()
    print("A Copy Named 'copy' Has Been Created In The Root Directory!")

    # 比较生成的copy和源文件
    if filecmp.cmp(file_path, drive_letter + '\\copy', shallow=False):
        print("'copy' Is The Same As Source File!")
    else:
        print("'copy' And Source File Differ!")
