import logging

from PIL import Image

from coilsnake.model.eb.fonts import EbFont, EbCreditsFont, FONT_IMAGE_PALETTE
from coilsnake.modules.eb.EbModule import EbModule
from coilsnake.model.eb.table import eb_table_from_offset
from coilsnake.util.common.image import open_indexed_image
from coilsnake.util.common.helper import patch
from coilsnake.util.common.yml import yml_load, yml_dump
from coilsnake.util.eb.pointer import from_snes_address, to_snes_address


log = logging.getLogger(__name__)

FONT_POINTER_TABLE_OFFSET = 0xC3F054
FONT_FILENAMES = ["0", "1", "3", "4", "2"]

CREDITS_GRAPHICS_ASM_POINTER = 0x4F1A7
CREDITS_PALETTES_ADDRESS = 0x21E914


class FontModule(EbModule):
    NAME = "Fonts"
    FREE_RANGES = [
        (0x21E528, 0x21E913),  # Credits font graphics
        (0x210C7A, 0x212EF9),  # Fonts 0, 2, 3, and 4
        (0x201359, 0x201FB8),  # Font 1
    ]

    def __init__(self):
        super(FontModule, self).__init__()
        self.font_pointer_table = eb_table_from_offset(offset=FONT_POINTER_TABLE_OFFSET)
        self.fonts = [
            EbFont(num_characters=224, tile_width=16, tile_height=16),
            EbFont(num_characters=224, tile_width=16, tile_height=16),
            EbFont(num_characters=224, tile_width=8, tile_height=16),
            EbFont(num_characters=224, tile_width=8, tile_height=8),
            EbFont(num_characters=224, tile_width=16, tile_height=16),
        ]
        self.credits_font = EbCreditsFont()

    def read_from_rom(self, rom):
        self.font_pointer_table.from_block(
            block=rom, offset=from_snes_address(FONT_POINTER_TABLE_OFFSET)
        )
        for i, font in enumerate(self.fonts):
            log.debug("Reading font #{} from the ROM".format(FONT_FILENAMES[i]))
            font.from_block(
                block=rom,
                tileset_offset=from_snes_address(self.font_pointer_table[i][1]),
                character_widths_offset=from_snes_address(
                    self.font_pointer_table[i][0]
                ),
            )

        self.read_credits_font_from_rom(rom)

    def write_to_rom(self, rom):
        self.font_pointer_table.from_block(
            block=rom, offset=from_snes_address(FONT_POINTER_TABLE_OFFSET)
        )
        for i, font in enumerate(self.fonts):
            log.debug("Writing font #{} to the ROM".format(FONT_FILENAMES[i]))

            graphics_offset, widths_offset = font.to_block(block=rom)
            self.font_pointer_table[i][0] = to_snes_address(widths_offset)
            self.font_pointer_table[i][1] = to_snes_address(graphics_offset)
        self.font_pointer_table.to_block(
            block=rom, offset=from_snes_address(FONT_POINTER_TABLE_OFFSET)
        )

        # patch the rom accordingly if the user uses 224 character fonts
        if all(font.num_characters == 224 for font in self.fonts):
            log.debug("Patching the ROM for 224 character font support")

            # AND #$007F -> NOP NOP NOP
            # this is used at $C19249:
            # something about printing numbers
            patch(rom, 3, 0xC19282, [0xEA, 0xEA, 0xEA])

            # SBC #$50   -> SBC #$20
            # AND #$007F -> NOP NOP NOP
            # this is used at $EF01D2:
            # Inserts a newline if printing chr would overflow the window
            patch(rom, 3, 0xEF01F5, [0xE9, 0x20, 0x00])
            patch(rom, 3, 0xEF01F8, [0xEA, 0xEA, 0xEA])

            # SBC #$50   -> SBC #$20
            # AND #$007F -> NOP NOP NOP
            # this is used at $C43E31:
            # Gets the render width, of pixels, of a given string using the focused window's font
            patch(rom, 3, 0xC43E6C, [0xE9, 0x20, 0x00])
            patch(rom, 3, 0xC43E6F, [0xEA, 0xEA, 0xEA])

            # SBC #$50   -> SBC #$20
            # AND #$007F -> NOP NOP NOP
            # this is used at $C440B5:
            # Prefills the input field for text entry screens
            patch(rom, 3, 0xC440E0, [0xE9, 0x20, 0x00])
            patch(rom, 3, 0xC440E3, [0xEA, 0xEA, 0xEA])

            # SBC #$50   -> SBC #$20
            # AND #$007F -> NOP NOP NOP
            # this is used at $C4424A:
            # Writes a character to the various text entry buffers
            patch(rom, 3, 0xC44272, [0xE9, 0x20, 0x00])
            patch(rom, 3, 0xC44275, [0xEA, 0xEA, 0xEA])

            # SBC #CHAR::SPACE -> SBC #$20
            # AND #$007F       -> NOP NOP NOP
            # this is used at $C444FB:
            # Renders text in small font directly to VRAM
            patch(rom, 3, 0xC4454A, [0xE9, 0x20, 0x00])
            patch(rom, 3, 0xC4454D, [0xEA, 0xEA, 0xEA])

            # SBC #$50   -> SBC #$20
            # AND #$007F -> NOP NOP NOP
            # this is used at $C445E1:
            # Looks ahead at text script and handles automatic newlines if the word is too long
            patch(rom, 3, 0xC44752, [0xE9, 0x20, 0x00])
            patch(rom, 3, 0xC44755, [0xEA, 0xEA, 0xEA])

            # SBC #$50   -> SBC #$20
            # AND #$007F -> NOP NOP NOP
            # this is used at $C44E61:
            # Prints a VWF character with the specified font to the focused window at the current cursor coordinates
            patch(rom, 3, 0xC44EEC, [0xE9, 0x20, 0x00])
            patch(rom, 3, 0xC44EEF, [0xEA, 0xEA, 0xEA])

            # SBC #$50   -> SBC #$20
            # AND #$007F -> NOP NOP NOP
            # this is used at $C44FF3:
            # Gets the width, in pixels, of a character string with padding included
            patch(rom, 3, 0xC4501D, [0xE9, 0x20, 0x00])
            patch(rom, 3, 0xC45020, [0xEA, 0xEA, 0xEA])

            # SBC #80   -> SBC #$20
            # AND #$007F -> NOP NOP NOP
            # this is used at $C47C3F:
            # Prepares text layer graphics for BG3
            patch(rom, 3, 0xC47D3B, [0xE9, 0x20, 0x00])
            patch(rom, 3, 0xC47D3E, [0xEA, 0xEA, 0xEA])

            # SBC #$50   -> SBC #$20
            # AND #$007F -> NOP NOP NOP
            # this is used at $C4999B:
            # Render a full large font character to the VWF buffer, adjusting flyoverByteOffset and flyoverPixelOffset as appropriate
            patch(rom, 3, 0xC48289, [0xE9, 0x20, 0x00])
            patch(rom, 3, 0xC4828C, [0xEA, 0xEA, 0xEA])

            # SBC #80   -> SBC #$20
            # AND #$007F -> NOP NOP NOP
            # this is used at $C4E583:
            # Renders text to tiles for the cast scene
            patch(rom, 3, 0xC4E5E6, [0xE9, 0x20, 0x00])
            patch(rom, 3, 0xC4E5E9, [0xEA, 0xEA, 0xEA])

            # LDA #32 -> LDA #$50
            # this is an hardcoded bullet point char ID
            # this is used at $C440B5:
            # Prefills the input field for text entry screens
            patch(rom, 2, 0xC44151, [0xA9, 0x50])

            # LDA #3 -> LDA #$33
            # this is an hardcoded middle dot char ID
            # this is used at $C440B5:
            # Prefills the input field for text entry screens
            patch(rom, 2, 0xC4418D, [0xA9, 0x33])

            # LDA #3 -> LDA #$33
            # this is an hardcoded middle dot char ID
            # this is used at $C441B7:
            # Clears the input field for text entry screens
            patch(rom, 3, 0xC441D5, [0xA9, 0x33, 0x00])

            # LDA #32 -> LDA #$50
            # this is an hardcoded bullet point char ID
            # this is used at $C441B7:
            # Clears the input field for text entry screens
            patch(rom, 2, 0xC441F9, [0xA9, 0x50])

        self.write_credits_font_to_rom(rom)

    def read_from_project(self, resource_open):
        for i, font in enumerate(self.fonts):
            with resource_open("Fonts/" + FONT_FILENAMES[i], "png") as image_file:
                with resource_open(
                    "Fonts/" + FONT_FILENAMES[i] + "_widths", "yml", True
                ) as widths_file:
                    font.from_files(
                        image_file, widths_file, image_format="png", widths_format="yml"
                    )

        self.read_credits_font_from_project(resource_open)

    def write_to_project(self, resource_open):
        for i, font in enumerate(self.fonts):
            # Write the PNG
            with resource_open("Fonts/" + FONT_FILENAMES[i], "png") as image_file:
                with resource_open(
                    "Fonts/" + FONT_FILENAMES[i] + "_widths", "yml", True
                ) as widths_file:
                    font.to_files(
                        image_file, widths_file, image_format="png", widths_format="yml"
                    )

        self.write_credits_font_to_project(resource_open)

    def read_credits_font_from_rom(self, rom):
        log.debug("Reading the credits font from the ROM")
        self.credits_font.from_block(
            block=rom,
            tileset_asm_pointer_offset=CREDITS_GRAPHICS_ASM_POINTER,
            palette_offset=CREDITS_PALETTES_ADDRESS,
        )

    def write_credits_font_to_rom(self, rom):
        log.debug("Writing the credits font to the ROM")
        self.credits_font.to_block(
            block=rom,
            tileset_asm_pointer_offset=CREDITS_GRAPHICS_ASM_POINTER,
            palette_offset=CREDITS_PALETTES_ADDRESS,
        )

    def write_credits_font_to_project(self, resource_open):
        with resource_open("Fonts/credits", "png") as image_file:
            self.credits_font.to_files(image_file, "png")

    def read_credits_font_from_project(self, resource_open):
        with resource_open("Fonts/credits", "png") as image_file:
            self.credits_font.from_files(image_file, "png")

    def upgrade_project(
        self,
        old_version,
        new_version,
        rom,
        resource_open_r,
        resource_open_w,
        resource_delete,
    ):
        if old_version == new_version:
            return
        elif old_version == 5:
            # Expand all the fonts from 96 characters to 128 characters
            for i, font in enumerate(self.fonts):
                log.debug("Expanding font #{}".format(FONT_FILENAMES[i]))
                image_resource_name = "Fonts/" + FONT_FILENAMES[i]
                widths_resource_name = "Fonts/" + FONT_FILENAMES[i] + "_widths"
                new_image_w, new_image_h = font.image_size()

                # Expand the image

                with resource_open_r(image_resource_name, "png") as image_file:
                    image = open_indexed_image(image_file)

                    expanded_image = Image.new("P", (new_image_w, new_image_h), None)
                    for y in range(new_image_h):
                        for x in range(new_image_w):
                            expanded_image.putpixel((x, y), 1)
                    FONT_IMAGE_PALETTE.to_image(expanded_image)
                    expanded_image.paste(image, (0, 0))

                    with resource_open_w(image_resource_name, "png") as image_file2:
                        expanded_image.save(image_file2, "png")

                # Expand the widths

                with resource_open_r(widths_resource_name, "yml", True) as widths_file:
                    widths_dict = yml_load(widths_file)

                for character_id in range(96, 128):
                    if character_id not in widths_dict:
                        widths_dict[character_id] = 0

                with resource_open_w(widths_resource_name, "yml", True) as widths_file:
                    yml_dump(widths_dict, widths_file, default_flow_style=False)

            self.upgrade_project(
                6, new_version, rom, resource_open_r, resource_open_w, resource_delete
            )
        elif old_version <= 2:
            # The credits font was a new feature in version 3

            self.read_credits_font_from_rom(rom)
            self.write_credits_font_to_project(resource_open_w)
            self.upgrade_project(
                3, new_version, rom, resource_open_r, resource_open_w, resource_delete
            )
        else:
            self.upgrade_project(
                old_version + 1,
                new_version,
                rom,
                resource_open_r,
                resource_open_w,
                resource_delete,
            )
