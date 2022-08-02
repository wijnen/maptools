all: \
	asm/page-0.asm \
	asm/page-1.asm \
	asm/page-2.asm \
	asm/page-3.asm \
	asm/page-4.asm \
	asm/page-5.asm \
	asm/page-6.asm \
	asm/page-7.asm \
	asm/page-8.asm \
	asm/page-9.asm \
	asm/page-a.asm \
	asm/page-b.asm \
	asm/page-c.asm \
	asm/page-d.asm \
	asm/page-e.asm \
	asm/page-f.asm

asm/page-0.asm: org=0x4000
asm/page-1.asm: org=0x6000
asm/page-2.asm: org=0x8000
asm/page-3.asm: org=0xa000
asm/page-4.asm: org=0x6000
asm/page-5.asm: org=0x8000
asm/page-6.asm: org=0xa000
asm/page-7.asm: org=0x6000
asm/page-8.asm: org=0x8000
asm/page-9.asm: org=0xa000
asm/page-a.asm: org=0x6000
asm/page-b.asm: org=0x8000
asm/page-c.asm: org=0xa000
asm/page-d.asm: org=0x6000
asm/page-e.asm: org=0x8000
asm/page-f.asm: org=0xa000

asm/page-%.asm: bin/page-%.bin Makefile symbols.txt blocks/blocks-%.txt
	z80dasm -a -l -g $(org) -o $@ -t $< -b $(patsubst asm/page-%.asm,blocks/blocks-%.txt,$@) -s asm/symbols-$(patsubst asm/page-%.asm,%,$@).out -S symbols.txt

bin:
	for i in `seq 0 15`; do dd if=nemesis.rom of=bin/page-`printf %x $$i`.bin skip=$$i count=1 bs=$$[0x2000] ; done

clean:
	rm -f asm/page-*.asm bin/page-*.bin

.PHONY: bin clean

SHELL = /bin/bash
