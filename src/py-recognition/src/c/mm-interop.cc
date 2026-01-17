#include<windows.h>
#include<propsys.h>
#include<mmdeviceapi.h>
#include<Functiondiscoverykeys_devpkey.h>
#include "stdio.h"
#pragma comment(lib, "Ole32.lib")

#define SAFE_RELEASE(punk)  \
    if ((punk) != NULL)  \
        { (punk)->Release(); (punk) = NULL; }

namespace {
    template<typename T>
    class ComIUnknownImpl : public T {

        LONG _cRef;
        T *_pComInterface;

    public:
        ComIUnknownImpl() : _cRef(1), _pComInterface(NULL) {}

        ~ComIUnknownImpl() {
            SAFE_RELEASE(_pComInterface)
        }


        ULONG STDMETHODCALLTYPE AddRef() {
            return InterlockedIncrement(&_cRef);
        }

        ULONG STDMETHODCALLTYPE Release() {
            ULONG ulRef = InterlockedDecrement(&_cRef);
            if(ulRef == 0) {
                delete this;
            }
            return ulRef;
        }

        HRESULT STDMETHODCALLTYPE QueryInterface(REFIID riid, VOID **ppvInterface) {
            if(IID_IUnknown == riid) {
                AddRef();
                *ppvInterface = (IUnknown*)this;
            } else if(__uuidof(T) == riid) {
                AddRef();
                *ppvInterface = (T*)this;
            } else {
                *ppvInterface = NULL;
                return E_NOINTERFACE;
            }
            return S_OK;
        }
    };

    struct MMNotificationClientCallback {
        void (CALLBACK *onDefaultDeviceChanged)(EDataFlow, ERole, LPCWSTR, LPCWSTR);
        void (CALLBACK *onDeviceAdded)(LPCWSTR, LPCWSTR);
        void (CALLBACK *onDeviceRemoved)(LPCWSTR, LPCWSTR);
        void (CALLBACK *onDeviceStateChanged)(LPCWSTR, long long, LPCWSTR);
    };

    class MMNotificationClient : public ComIUnknownImpl<IMMNotificationClient> {
    private:
        MMNotificationClientCallback _callback;

    public:
        MMNotificationClient(MMNotificationClientCallback _callback) :  _callback(_callback) {}


        HRESULT STDMETHODCALLTYPE OnDefaultDeviceChanged(
            EDataFlow flow,
            ERole role,
            LPCWSTR pwstrDeviceId){

            PROPVARIANT varString;
            PropVariantInit(&varString);
            this->GetDeviceName(pwstrDeviceId, &varString);
            this->_callback.onDefaultDeviceChanged(flow, role, pwstrDeviceId, varString.pwszVal);
            PropVariantClear(&varString);
            return S_OK;
        }

        HRESULT STDMETHODCALLTYPE OnDeviceAdded(LPCWSTR pwstrDeviceId) {
            PROPVARIANT varString;
            PropVariantInit(&varString);
            this->GetDeviceName(pwstrDeviceId, &varString);
            this->_callback.onDeviceAdded(pwstrDeviceId, varString.pwszVal);
            PropVariantClear(&varString);

            return S_OK;
        };

        HRESULT STDMETHODCALLTYPE OnDeviceRemoved(LPCWSTR pwstrDeviceId) {
            PROPVARIANT varString;
            PropVariantInit(&varString);
            this->GetDeviceName(pwstrDeviceId, &varString);
            this->_callback.onDeviceRemoved(pwstrDeviceId, varString.pwszVal);
            PropVariantClear(&varString);

            return S_OK;
        }

        HRESULT STDMETHODCALLTYPE OnDeviceStateChanged(LPCWSTR pwstrDeviceId, DWORD dwNewState) {
            PROPVARIANT varString;
            PropVariantInit(&varString);
            this->GetDeviceName(pwstrDeviceId, &varString);
            this->_callback.onDeviceStateChanged(pwstrDeviceId, dwNewState, varString.pwszVal);
            PropVariantClear(&varString);
            return S_OK;
        }

        HRESULT STDMETHODCALLTYPE OnPropertyValueChanged(LPCWSTR pwstrDeviceId, const PROPERTYKEY key){
            /*
            this->PrintDeviceName(pwstrDeviceId);
            printf("  -->Changed device property "
                "{%8.8x-%4.4x-%4.4x-%2.2x%2.2x-%2.2x%2.2x%2.2x%2.2x%2.2x%2.2x}#%d\n",
                key.fmtid.Data1, key.fmtid.Data2, key.fmtid.Data3,
                key.fmtid.Data4[0], key.fmtid.Data4[1],
                key.fmtid.Data4[2], key.fmtid.Data4[3],
                key.fmtid.Data4[4], key.fmtid.Data4[5],
                key.fmtid.Data4[6], key.fmtid.Data4[7],
                key.pid);
            */
            return S_OK;
        }

    private:
        HRESULT GetDeviceName(LPCWSTR pwstrId, PROPVARIANT *varString) {
            HRESULT hr = S_OK;
            IMMDevice *pDevice = NULL;
            IPropertyStore *pProps = NULL;

            CoInitialize(NULL);
            IMMDeviceEnumerator *_pEnum = NULL;

            if (_pEnum == NULL)
            {
                // Get enumerator for audio endpoint devices.
                hr = CoCreateInstance(__uuidof(MMDeviceEnumerator),
                    NULL, CLSCTX_INPROC_SERVER,
                    __uuidof(IMMDeviceEnumerator),
                    (void**)&_pEnum);
            }
            if (hr == S_OK)
            {
                hr = _pEnum->GetDevice(pwstrId, &pDevice);
            }
            if (hr == S_OK)
            {
                hr = pDevice->OpenPropertyStore(STGM_READ, &pProps);
            }
            if (hr == S_OK)
            {
                // Get the endpoint device's friendly-name property.
                hr = pProps->GetValue(PKEY_Device_FriendlyName, varString);
            }

            SAFE_RELEASE(pProps);
            SAFE_RELEASE(pDevice);
            CoUninitialize();
            return hr;
        }
    };

    IMMDeviceEnumerator *gs_pMMDeviceEnumerator = NULL;
    MMNotificationClient *gs_pMMNotificationClient = NULL;
}

extern "C" __declspec(dllexport) bool WINAPI Attach(
    void (*onDefaultDeviceChanged)(EDataFlow, ERole, LPCWSTR, LPCWSTR),
    void (*onDeviceAdded)(LPCWSTR, LPCWSTR),
    void (*onDeviceRemoved)(LPCWSTR, LPCWSTR),
    void (*onDeviceStateChanged)(LPCWSTR, long long, LPCWSTR)) {

    if(gs_pMMDeviceEnumerator) {
        return false;
    }
    CoInitializeEx(NULL, COINIT_APARTMENTTHREADED | COINIT_DISABLE_OLE1DDE);
    if(CoCreateInstance(
        __uuidof(MMDeviceEnumerator),
        NULL,
        CLSCTX_INPROC_SERVER,
        IID_PPV_ARGS(&gs_pMMDeviceEnumerator)) == S_OK) {

        gs_pMMNotificationClient = new MMNotificationClient({
            onDefaultDeviceChanged,
            onDeviceAdded,
            onDeviceRemoved,
            onDeviceStateChanged
        });
        if(gs_pMMDeviceEnumerator->RegisterEndpointNotificationCallback(gs_pMMNotificationClient) == S_OK) {
            return true;
        }
    }

    SAFE_RELEASE(gs_pMMNotificationClient);
    SAFE_RELEASE(gs_pMMDeviceEnumerator);
    return false;
}

extern "C" __declspec(dllexport) bool WINAPI IsCaptureDevice(LPCWSTR pwstrId) {
    if(!gs_pMMDeviceEnumerator) {
        return false;
    }

    bool result = false;
    IMMDevice *pDevice = NULL;
    IPropertyStore *pProps = NULL;
    PROPVARIANT factor;

    PropVariantInit(&factor);
    if(gs_pMMDeviceEnumerator->GetDevice(pwstrId, &pDevice) == S_OK) {
        if(pDevice->OpenPropertyStore(STGM_READ, &pProps) != S_OK) {
            goto end;
        }
        if(pProps->GetValue(PKEY_Device_FriendlyName, &factor) != S_OK) {
            goto end;
        }
        result = factor.uintVal == Handset || factor.uintVal == Microphone;
    }
end:
    PropVariantClear(&factor);

    SAFE_RELEASE(pProps)
    SAFE_RELEASE(pDevice)
    return result;
}

BOOL WINAPI DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID lpvReserved ) {
    return TRUE;
}
