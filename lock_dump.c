#include <windows.h>
#include <aclapi.h>

// Ta funkcja sprawi, że Task Manager powie "Odmowa dostępu"
__declspec(dllexport) void secure_isolate_process()
{
    HANDLE hProcess = GetCurrentProcess();

    // Ustawiamy pusty (ale nie NULL!) DACL.
    // Pusty DACL oznacza: "Nikt nie ma żadnych uprawnień do tego obiektu".
    // Nawet PROCESS_QUERY_INFORMATION czy PROCESS_VM_READ zostaną zablokowane.

    PACL pEmptyDacl = (PACL)LocalAlloc(LPTR, sizeof(ACL));
    InitializeAcl(pEmptyDacl, sizeof(ACL), ACL_REVISION);

    DWORD res = SetSecurityInfo(
        hProcess,
        SE_KERNEL_OBJECT,
        DACL_SECURITY_INFORMATION,
        NULL,       // Owner
        NULL,       // Group
        pEmptyDacl, // Nasz pusty DACL
        NULL        // SACL
    );

    if (res == ERROR_SUCCESS)
    {
        // Sukces - od teraz proces jest w bunkrze
    }

    LocalFree(pEmptyDacl);
}
