# Copyright (c) 2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText

from easy_enum import Enum


########################################################################################################################
# McuBoot Commands Tag
########################################################################################################################

class CommandTag(Enum):
    """ McuBoot Commands """

    FLASH_ERASE_ALL = (0x01, 'FlashEraseAll', 'Erase Complete Flash')
    FLASH_ERASE_REGION = (0x02, 'FlashEraseRegion', 'Erase Flash Region')
    READ_MEMORY = (0x03, 'ReadMemory', 'Read Memory')
    WRITE_MEMORY = (0x04, 'WriteMemory', 'Write Memory')
    FILL_MEMORY = (0x05, 'FillMemory', 'Fill Memory')
    FLASH_SECURITY_DISABLE = (0x06, 'FlashSecurityDisable', 'Disable Flash Security')
    GET_PROPERTY = (0x07, 'GetProperty', 'Get Property')
    RECEIVE_SB_FILE = (0x08, 'ReceiveSBFile', 'Receive SB File')
    EXECUTE = (0x09, 'Execute', 'Execute')
    CALL = (0x0A, 'Call', 'Call')
    RESET = (0x0B, 'Reset', 'Reset MCU')
    SET_PROPERTY = (0x0C, 'SetProperty', 'Set Property')
    FLASH_ERASE_ALL_UNSECURE = (0x0D, 'FlashEraseAllUnsecure', 'Erase Complete Flash and Unlock')
    FLASH_PROGRAM_ONCE = (0x0E, 'FlashProgramOnce', 'Flash Program Once')
    FLASH_READ_ONCE = (0x0F, 'FlashReadOnce', 'Flash Read Once')
    FLASH_READ_RESOURCE = (0x10, 'FlashReadResource', 'Flash Read Resource')
    CONFIGURE_MEMORY = (0x11, 'ConfigureMemory', 'Configure Quad-SPI Memory')
    RELIABLE_UPDATE = (0x12, 'ReliableUpdate', 'Reliable Update')
    GENERATE_KEY_BLOB = (0x13, 'GenerateKeyBlob', 'Generate Key Blob')
    KEY_PROVISIONING = (0x15, 'KeyProvisioning', 'Key Provisioning')
    Flash_IMAGE = (0x16, 'FlashImage', 'Flash Image')

    # reserved commands
    CONFIGURE_I2C = (0xC1, 'ConfigureI2c', 'Configure I2C')
    CONFIGURE_SPI = (0xC2, 'ConfigureI2c', 'Configure SPI')
    CONFIGURE_CAN = (0xC3, 'ConfigureCan', 'Configure CAN')

    # GENERIC_RESPONSE = (0xA0, 'GenericResponse', 'Generic Response')
    # FLASH_READ_ONCE_RESPONSE = (0xAF, 'FlashReadOnceResponse', 'Flash Read Once Response')
    # FLASH_READ_RESOURCE_RESPONSE = (0xB0, 'FlashReadResourceResponse', 'Flash Read Resource Response')
    # GENERATE_KEY_BLOB_RESPONSE = (0xB3, 'GenerateKeyBlobResponse', 'Generate Key Blob Response')
    # KEY_PROVISIONING_RESPONSE = (0xB5, 'KeyProvisionResponse', 'Key Provision Response')

########################################################################################################################
# McuBoot Properties Tag
########################################################################################################################

class PropertyTag(Enum):
    """ McuBoot Properties """

    LIST_PROPERTIES = (0x00, 'ListProperties', 'List Properties')
    CURRENT_VERSION = (0x01, 'CurrentVersion', 'Current Version')
    AVAILABLE_PERIPHERALS = (0x02, 'AvailablePeripherals', 'Available Peripherals')
    FLASH_START_ADDRESS = (0x03, 'FlashStartAddress', 'Flash Start Address')
    FLASH_SIZE = (0x04, 'FlashSize', 'Flash Size')
    FLASH_SECTOR_SIZE = (0x05, 'FlashSectorSize', 'Flash Sector Size')
    FLASH_BLOCK_COUNT = (0x06, 'FlashBlockCount', 'Flash Block Count')
    AVAILABLE_COMMANDS = (0x07, 'AvailableCommands', 'Available Commands')
    CRC_CHECK_STATUS = (0x08, 'CrcCheckStatus', 'CRC Check Status')
    VERIFY_WRITES = (0x0A, 'VerifyWrites', 'Verify Writes')
    MAX_PACKET_SIZE = (0x0B, 'MaxPacketSize', 'Max Packet Size')
    RESERVED_REGIONS = (0x0C, 'ReservedRegions', 'Reserved Regions')
    VALIDATE_REGIONS = (0x0D, 'ValidateRegions', 'Validate Regions')
    RAM_START_ADDRESS = (0x0E, 'RAMStartAddress', 'RAM Start Address')
    RAM_SIZE = (0x0F, 'RAMSize', 'RAM Size')
    SYSTEM_DEVICE_IDENT = (0x10, 'SystemDeviceIdent', 'System Device Identification')
    FLASH_SECURITY_STATE = (0x11, 'FlashSecurityState', 'Flash Security State')
    UNIQUE_DEVICE_IDENT = (0x12, 'UniqueDeviceIdent', 'Unique Device Identification')
    FLASH_FAC_SUPPORT = (0x13, 'FlashFacSupport', 'Flash Fac. Support')
    FLASH_ACCESS_SEGMENT_SIZE = (0x14, 'FlashAccessSegmentSize', 'Flash Access Segment Size')
    FLASH_ACCESS_SEGMENT_COUNT = (0x15, 'FlashAccessSegmentCount', 'Flash Access Segment Count')
    FLASH_READ_MARGIN = (0x16, 'FlashReadMargin', 'Flash Read Margin')
    QSPI_INIT_STATUS = (0x17, 'QspiInitStatus', 'QuadSPI Initialization Status')
    TARGET_VERSION = (0x18, 'TargetVersion', 'Target Version')
    EXTERNAL_MEMORY_ATTRIBUTES = (0x19, 'ExternalMemoryAttributes', 'External Memory Attributes')
    RELIABLE_UPDATE_STATUS = (0x1A, 'ReliableUpdateStatus', 'Reliable Update Status')
    FLASH_PAGE_SIZE = (0x1B, 'FlashPageSize', 'Flash Page Size')
    IRQ_NOTIFIER_PIN = (0x1C, 'IrqNotifierPin', 'Irq Notifier Pin')
    PFR_KEYSTORE_UPDATE_OPT = (0x1D, 'PfrKeystoreUpdateOpt', 'PFR Keystore Update Opt')


########################################################################################################################
# McuBoot Status Code
########################################################################################################################

class StatusCode(Enum):
    """ McuBoot status codes """

    SUCCESS = (0, 'Success', 'Success')
    FAIL = (1, 'Fail', 'Fail')
    READ_ONLY = (2, 'ReadOnly', 'Read Only Error')
    OUT_OF_RANGE = (3, 'OutOfRange', 'Out Of Range Error')
    INVALID_ARGUMENT = (4, 'InvalidArgument', 'Invalid Argument Error')
    TIMEOUT = (5, 'Timeout', 'Timeout Error')
    NO_TRANSFER_IN_PROGRESS = (6, 'NoTransferInProgress', 'No Transfer In Progress Error')

    # Flash driver errors.
    FLASH_SIZE_ERROR = (100, 'FlashSizeError', 'FLASH Driver: Size Error')
    FLASH_ALIGNMENT_ERROR = (101, 'FlashAlignmentError', 'FLASH Driver: Alignment Error')
    FLASH_ADDRESS_ERROR = (102, 'FlashAddressError', 'FLASH Driver: Address Error')
    FLASH_ACCESS_ERROR = (103, 'FlashAccessError', 'FLASH Driver: Access Error')
    FLASH_PROTECTION_VIOLATION = (104, 'FlashProtectionViolation', 'FLASH Driver: Protection Violation')
    FLASH_COMMAND_FAILURE = (105, 'FlashCommandFailure', 'FLASH Driver: Command Failure')
    FLASH_UNKNOWN_PROPERTY = (106, 'FlashUnknownProperty', 'FLASH Driver: Unknown Property')
    FLASH_REGION_EXECUTE_ONLY = (108, 'FlashRegionExecuteOnly', 'FLASH Driver: Region Execute Only')
    FLASH_EXEC_IN_RAM_NOT_READY = (109, 'FlashExecuteInRamFunctionNotReady','FLASH Driver: Execute In Ram Function Not Ready')
    FLASH_COMMAND_NOT_SUPPORTED = (111, 'FlashCommandNotSupported', 'FLASH Driver: Command Not Supported')
    FLASH_OUT_OF_DATE_CFPA_PAGE = (132, 'FlashOutOfDateCfpaPage', 'FLASH Driver: Out Of Date CFPA Page')

    # I2C driver errors.
    I2C_SLAVE_TX_UNDERRUN = (200, 'I2cSlaveTxUnderrun', 'I2C Driver: Slave Tx Underrun')
    I2C_SLAVE_RX_OVERRUN = (201, 'I2cSlaveRxOverrun', 'I2C Driver: Slave Rx Overrun')
    I2C_ARBITRATION_LOST = (202, 'I2cArbitrationLost', 'I2C Driver: Arbitration Lost')

    # SPI driver errors.
    SPI_SLAVE_TX_UNDERRUN = (300, 'SpiSlaveTxUnderrun', 'SPI Driver: Slave Tx Underrun')
    SPI_SLAVE_RX_OVERRUN = (301, 'SpiSlaveRxOverrun', 'SPI Driver: Slave Rx Overrun')

    # QuadSPI driver errors
    QSPI_FLASH_SIZE_ERROR = (400, 'QspiFlashSizeError', 'QSPI Driver: Flash Size Error')
    QSPI_FLASH_ALIGNMENT_ERROR = (401, 'QspiFlashAlignmentError', 'QSPI Driver: Flash Alignment Error')
    QSPI_FLASH_ADDRESS_ERROR = (402, 'QspiFlashAddressError', 'QSPI Driver: Flash Address Error')
    QSPI_FLASH_COMMAND_FAILURE = (403, 'QspiFlashCommandFailure', 'QSPI Driver: Flash Command Failure')
    QSPI_FLASH_UNKNOWN_PROPERTY = (404, 'QspiFlashUnknownProperty', 'QSPI Driver: Flash Unknown Property')
    QSPI_NOT_CONFIGURED = (405, 'QspiNotConfigured', 'QSPI Driver: Not Configured')
    QSPI_COMMAND_NOT_SUPPORTED = (406, 'QspiCommandNotSupported', 'QSPI Driver: Command Not Supported')
    QSPI_COMMAND_TIMEOUT = (407, 'QspiCommandTimeout', 'QSPI Driver: Command Timeout')
    QSPI_WRITE_FAILURE = (408, 'QspiWriteFailure', 'QSPI Driver: Write Failure')

    # OTFAD driver errors.
    OTFAD_SECURITY_VIOLATION = (500, 'OtfadSecurityViolation', 'OTFAD Driver: Security Violation')
    OTFAD_LOGICALLY_DISABLED = (501, 'OtfadLogicallyDisabled', 'OTFAD Driver: Logically Disabled')
    OTFAD_INVALID_KEY = (502, 'OtfadInvalidKey', 'OTFAD Driver: Invalid Key')
    OTFAD_INVALID_KEY_BLOB = (503, 'OtfadInvalidKeyBlob', 'OTFAD Driver: Invalid Key Blob')

    # SDMMC driver errors.

    # Bootloader errors.
    UNKNOWN_COMMAND = (10000, 'UnknownCommand', 'Unknown Command')
    SECURITY_VIOLATION = (10001, 'SecurityViolation', 'Security Violation')
    ABORT_DATA_PHASE = (10002, 'AbortDataPhase', 'Abort Data Phase')
    PING_ERROR = (10003, 'PingError', 'Ping Error')
    NO_RESPONSE = (10004, 'NoResponse', 'No Response')
    NO_RESPONSE_EXPECTED = (10005, 'NoResponseExpected', 'No Response Expected')
    UNSUPPORTED_COMMAND = (10006, 'UnsupportedCommand', 'Unsupported Command')

    # SB loader errors.
    ROMLDR_SECTION_OVERRUN = (10100, 'RomLdrSectionOverrun', 'ROM Loader: Section Overrun')
    ROMLDR_SIGNATURE = (10101, 'RomLdrSignature', 'ROM Loader: Signature Error')
    ROMLDR_SECTION_LENGTH = (10102, 'RomLdrSectionLength', 'ROM Loader: Section Length Error')
    ROMLDR_UNENCRYPTED_ONLY = (10103, 'RomLdrUnencryptedOnly', 'ROM Loader: Unencrypted Only')
    ROMLDR_EOF_REACHED = (10104, 'RomLdrEOFReached', 'ROM Loader: EOF Reached')
    ROMLDR_CHECKSUM = (10105, 'RomLdrChecksum', 'ROM Loader: Checksum Error')
    ROMLDR_CRC32_ERROR = (10106, 'RomLdrCrc32Error', 'ROM Loader: CRC32 Error')
    ROMLDR_UNKNOWN_COMMAND = (10107, 'RomLdrUnknownCommand', 'ROM Loader: Unknown Command')
    ROMLDR_ID_NOT_FOUND = (10108, 'RomLdrIdNotFound', 'ROM Loader: ID Not Found')
    ROMLDR_DATA_UNDERRUN = (10109, 'RomLdrDataUnderrun', 'ROM Loader: Data Underrun')
    ROMLDR_JUMP_RETURNED = (10110, 'RomLdrJumpReturned', 'ROM Loader: Jump Returned')
    ROMLDR_CALL_FAILED = (10111, 'RomLdrCallFailed', 'ROM Loader: Call Failed')
    ROMLDR_KEY_NOT_FOUND = (10112, 'RomLdrKeyNotFound', 'ROM Loader: Key Not Found')
    ROMLDR_SECURE_ONLY = (10113, 'RomLdrSecureOnly', 'ROM Loader: Secure Only')
    ROMLDR_RESET_RETURNED = (10114, 'RomLdrResetReturned', 'ROM Loader: Reset Returned')
    ROMLDR_ROLLBACK_BLOCKED = (10115, 'RomLdrRollbackBlocked', 'ROM Loader: Rollback Blocked')
    ROMLDR_INVALID_SECTION_MAC_COUNT = (10116, 'RomLdrInvalidSectionMacCount', 'ROM Loader: Invalid Section Mac Count')
    ROMLDR_UNEXPECTED_COMMAND = (10117, 'RomLdrUnexpectedCommand', 'ROM Loader: Unexpected Command')

    # Memory interface errors.
    MEMORY_RANGE_INVALID = (10200, 'MemoryRangeInvalid', 'Memory Range Invalid')
    MEMORY_READ_FAILED = (10201, 'MemoryReadFailed', 'Memory Read Failed')
    MEMORY_WRITE_FAILED = (10202, 'MemoryWriteFailed', 'Memory Write Failed')
    MEMORY_CUMULATIVE_WRITE = (10203, 'MemoryCumulativeWrite', 'Memory Cumulative Write')
    MEMORY_APP_OVERLAP_WITH_EXECUTE_ONLY_REGION = (10204, 'MemoryAppOverlapWithExecuteOnlyRegion', 'Memory App Overlap With Execute Only Region')
    MEMORY_NOT_CONFIGURED = (10205, 'MemoryNotConfigured', 'Memory Not Configured')
    MEMORY_ALIGNMENT_ERROR = (10206, 'MemoryAlignmentError', 'Memory Alignment Error')
    MEMORY_VERIFY_FAILED = (10207, 'MemoryVerifyFailed', 'Memory Verify Failed')
    MEMORY_WRITE_PROTECTED = (10208, 'MemoryWriteProtected', 'Memory Write Protected')
    MEMORY_ADDRESS_ERROR = (10209, 'MemoryAddressError', 'Memory Address Error')
    MEMORY_BLANK_CHECK_FAILED = (10210, 'MemoryBlankCheckFailed', 'Memory Blank Check Failed')
    MEMORY_BLANK_PAGE_READ_DISALLOWED = (10211, 'MemoryBlankPageReadDisallowed', 'Memory Blank Page Read Disallowed')
    MEMORY_PROTECTED_PAGE_READ_DISALLOWED = (10212, 'MemoryProtectedPageReadDisallowed', 'Memory Protected Page Read Disallowed')
    MEMORY_FFR_SPEC_REGION_WRITE_BROKEN = (10213, 'MemoryFfrSpecRegionWriteBroken', 'Memory Ffr Spec Region Write Broken')
    MEMORY_UNSUPPORTED_COMMAND = (10214, 'MemoryUnsupportedCommand', 'Memory Unsupported Command')

    # Property store errors.
    UNKNOWN_PROPERTY = (10300, 'UnknownProperty', 'Unknown Property')
    READ_ONLY_PROPERTY = (10301, 'ReadOnlyProperty', 'Read Only Property')
    INVALID_PROPERTY_VALUE = (10302, 'InvalidPropertyValue', 'Invalid Property Value')

    # Property store errors.
    APP_CRC_CHECK_PASSED = (10400, 'AppCrcCheckPassed', 'Application CRC Check: Passed')
    APP_CRC_CHECK_FAILED = (10401, 'AppCrcCheckFailed', 'Application: CRC Check: Failed')
    APP_CRC_CHECK_INACTIVE = (10402, 'AppCrcCheckInactive', 'Application CRC Check: Inactive')
    APP_CRC_CHECK_INVALID = (10403, 'AppCrcCheckInvalid', 'Application CRC Check: Invalid')
    APP_CRC_CHECK_OUT_OF_RANGE = (10404, 'AppCrcCheckOutOfRange', 'Application CRC Check: Out Of Range')

    # Packetizer errors.
    NO_PING_RESPONSE = (10500, 'NoPingResponse', 'No response received for ping command.')
    INVALID_PACKET_TYPE = (10501, 'InvalidPacketType', 'Invalid packet type.')
    INVALID_CRC = (10502, 'InvalidCRC', 'Invalid CRC value.')
    NO_COMMAND_RESPONSE = (10503, 'NoCommandResponse', 'No response received for command.')

    # Reliable update errors.
    RELIABLE_UPDATE_SUCCESS = (10600, 'ReliableUpdateSuccess', 'Reliable Update Success')

########################################################################################################################
# McuBoot Memory ID
########################################################################################################################

class ExtMemId(Enum):
    """ McuBoot External Memory Property Tags """

    QUAD_SPI0 = (1, 'QuadSPI', 'Quad SPI Memory 0')     #0x001
    # IFR0 = (4, 'Nonvolatile information register 0 (only used by SB loader)')
    SEMC_NOR = (8, 'SEMC NOR Memory')           #0x008
    FLEX_SPI_NOR = (9, 'Flex SPI NOR Memory')   #0x009
    SPIFI_NOR = (10, 'SPIFI NOR Memory')        #0x00a
    FLASH_EXECUTE_ONLY = (16, 'Execute-Only region on internal Flash')  #0x010
    SEMC_NAND = (256, 'SEMC NAND Memory')               #0x100
    SPI_NAND = (257, 'SPI NAND Memory')                 #0x101
    SPI_NOR_EEPROM = (272, 'SPI NOR/EEPROM Memory')     #0x100
    I2C_NOR_EEPROM = (273, 'I2C NOR/EEPROM Memory')     #0x111
    SD_CARD = (288, 'eSD, SD, SDHC, SDXC Memory Card')  #0x120
    MMC_CARD = (289, 'MMC, eMMC Memory Card')           #0x121


########################################################################################################################
# McuBoot External Memory Property Tags
########################################################################################################################

class ExtMemPropTags(Enum):
    """ McuBoot External Memory Property Tags """

    INIT_STATUS = 0x00000000
    START_ADDRESS = 0x00000001
    SIZE_IN_KBYTES = 0x00000002
    PAGE_SIZE = 0x00000004
    SECTOR_SIZE = 0x00000008
    BLOCK_SIZE = 0x00000010
