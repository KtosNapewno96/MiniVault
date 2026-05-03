; scrub.asm - Bezpieczne zerowanie pamięci
; Kompilacja: nasm -f win64 scrub.asm -o scrub.o

section .text
global secure_scrub_memory

secure_scrub_memory:
    ; RCX = adres bufora (pointer)
    ; RDX = rozmiar w bajtach (size_t)
    
    test rcx, rcx       ; Sprawdź czy adres nie jest nullem
    jz .done
    test rdx, rdx       ; Sprawdź czy rozmiar > 0
    jz .done

    mov rdi, rcx        ; RDI = cel dla stosb
    mov rcx, rdx        ; RCX = licznik dla rep
    xor rax, rax        ; RAX = 0 (wartość do wypełnienia)
    
    rep stosb           ; Wypełnia pamięć: [RDI] = AL, RDI++, RCX-- aż RCX=0

    ; Bariera pamięci (opcjonalnie, dla pewności zapisu przed powrotem)
    mfence

.done:
    ret
