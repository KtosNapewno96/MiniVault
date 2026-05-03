
section .text
global secure_scrub_memory

secure_scrub_memory:
    ; RCX = adres bufora (pointer)
    ; RDX = rozmiar w bajtach (size_t)
    
    test rcx, rcx       
    jz .done
    test rdx, rdx       
    jz .done

    mov rdi, rcx        
    mov rcx, rdx        
    xor rax, rax        
    
    rep stosb          


    mfence

.done:
    ret