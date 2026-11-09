// =============================================================================
// chrome_shell_stubs.cc — Stub implementations for 9 undefined references
// =============================================================================

// === chrome_pdf::PPP_* stubs ===
namespace chrome_pdf {

void* PPP_GetInterface(const char* interface_name) {
    return nullptr;
}

int PPP_InitializeModule(int module_id,
                          const void* (*get_browser_interface)(const char*)) {
    (void)module_id;
    (void)get_browser_interface;
    return 0;
}

void PPP_ShutdownModule() {
}

}  // namespace chrome_pdf


// === SafeBrowsing stubs ===
// IMPORTANT: include tracked_preference_validation_delegate.h BEFORE
// safe_browsing_service.h — otherwise scoped_ptr<TrackedPreferenceValidationDelegate>
// in safe_browsing_service.h will see only forward-declared (incomplete) type
// and fail to instantiate (sizeof(incomplete type) error).
#include "chrome/browser/prefs/tracked/tracked_preference_validation_delegate.h"
#include "chrome/browser/safe_browsing/safe_browsing_service.h"
#include "chrome/browser/safe_browsing/ui_manager.h"
#include "chrome/browser/safe_browsing/safe_browsing_blocking_page.h"
#include "base/memory/ref_counted.h"
#include "base/memory/scoped_ptr.h"

// === SafeBrowsingService::OnResourceRequest ===
void SafeBrowsingService::OnResourceRequest(const net::URLRequest* request) {
    (void)request;
}

// === SafeBrowsingService::ui_manager ===
// Returns const scoped_refptr<SafeBrowsingUIManager>&
namespace {
    scoped_refptr<SafeBrowsingUIManager> g_empty_ui_manager;
}
const scoped_refptr<SafeBrowsingUIManager>& SafeBrowsingService::ui_manager() const {
    return g_empty_ui_manager;
}

// === SafeBrowsingService::CreatePreferenceValidationDelegate ===
// Returns scoped_ptr<TrackedPreferenceValidationDelegate>
// (TrackedPreferenceValidationDelegate already included above)
scoped_ptr<TrackedPreferenceValidationDelegate>
SafeBrowsingService::CreatePreferenceValidationDelegate(Profile* profile) const {
    (void)profile;
    return scoped_ptr<TrackedPreferenceValidationDelegate>(nullptr);
}

// === SafeBrowsingUIManager::UnsafeResource constructor/destructor ===
SafeBrowsingUIManager::UnsafeResource::UnsafeResource() {
}

SafeBrowsingUIManager::UnsafeResource::~UnsafeResource() {
}

// === SafeBrowsingBlockingPage::CreateBlockingPage ===
// Returns SafeBrowsingBlockingPage*
namespace content { class WebContents; }
SafeBrowsingBlockingPage* SafeBrowsingBlockingPage::CreateBlockingPage(
    SafeBrowsingUIManager* manager,
    content::WebContents* web_contents,
    const UnsafeResource& resource) {
    (void)manager;
    (void)web_contents;
    (void)resource;
    return nullptr;
}
