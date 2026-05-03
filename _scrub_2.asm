; _scrub_2.asm
default rel
section .text
global secure_scrub_argon2
global DllMain

DllMain:
    mov eax, 1
    ret

secure_scrub_argon2:
    test rcx, rcx
    jz .done
    test rdx, rdx
    jz .done

    pxor xmm0, xmm0

.loop:
    cmp rdx, 16
    jl .remainder
    movdqu [rcx], xmm0
    add rcx, 16
    sub rdx, 16
    jnz .loop
    jmp .finalize

.remainder:
    test rdx, rdx
    jz .finalize
    mov byte [rcx], 0
    inc rcx
    dec rdx
    jnz .remainder

.finalize:
    mfence
.done:
    ret