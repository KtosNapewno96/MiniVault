#include <windows.h>
#include <aclapi.h>

__declspec(dllexport) void secure_isolate_process()
{
    HANDLE hProcess = GetCurrentProcess();


    PACL pEmptyDacl = (PACL)LocalAlloc(LPTR, sizeof(ACL));
    InitializeAcl(pEmptyDacl, sizeof(ACL), ACL_REVISION);

    DWORD res = SetSecurityInfo(
        hProcess,
        SE_KERNEL_OBJECT,
        DACL_SECURITY_INFORMATION,
        NULL,
        NULL,
        pEmptyDacl,
        NULL
    );

    if (res == ERROR_SUCCESS)
    {
        // Success
    }

    LocalFree(pEmptyDacl);
}
