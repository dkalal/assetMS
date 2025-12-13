/**
 * Security Testing Suite
 * Tests security measures, CSP, XSS protection, and authentication
 */

class SecurityTestSuite {
    constructor() {
        this.results = {};
        this.vulnerabilities = [];
    }

    async runAllTests() {
        console.log('🔒 Starting Security Tests');
        
        const tests = [
            { name: 'CSP Headers', test: () => this.testCSPHeaders() },
            { name: 'XSS Protection', test: () => this.testXSSProtection() },
            { name: 'CSRF Protection', test: () => this.testCSRFProtection() },
            { name: 'Input Sanitization', test: () => this.testInputSanitization() },
            { name: 'Authentication Security', test: () => this.testAuthSecurity() },
            { name: 'Cloud Domain Security', test: () => this.testCloudDomainSecurity() }
        ];

        for (const test of tests) {
            try {
                const result = await test.test();
                this.results[test.name] = result;
                console.log(`${result.status === 'PASSED' ? '✅' : '❌'} ${test.name}: ${result.status}`);
            } catch (error) {
                this.results[test.name] = { status: 'ERROR', error: error.message };
                console.log(`❌ ${test.name}: ERROR - ${error.message}`);
            }
        }

        return this.generateSecurityReport();
    }

    testCSPHeaders() {
        const cspMeta = document.querySelector('meta[http-equiv="Content-Security-Policy"]');
        const cspHeader = this.getCSPFromResponse();
        
        // Check if hardcoded CSP meta tag exists (should not)
        if (cspMeta) {
            this.vulnerabilities.push({
                type: 'CSP_HARDCODED',
                severity: 'HIGH',
                description: 'Hardcoded CSP meta tag found - should use middleware'
            });
        }
        
        // Check for required CSP directives
        const requiredDirectives = [
            'default-src',
            'script-src',
            'style-src',
            'img-src',
            'connect-src'
        ];
        
        const missingDirectives = [];
        if (cspHeader) {
            requiredDirectives.forEach(directive => {
                if (!cspHeader.includes(directive)) {
                    missingDirectives.push(directive);
                }
            });
        }
        
        const status = !cspMeta && missingDirectives.length === 0 ? 'PASSED' : 'FAILED';
        
        return {
            status,
            hardcodedCSP: !!cspMeta,
            missingDirectives,
            details: `CSP implementation: ${!cspMeta ? 'Middleware-based ✓' : 'Hardcoded ✗'}`
        };
    }

    testXSSProtection() {
        const testPayloads = [
            '<script>alert("xss")</script>',
            'javascript:alert("xss")',
            '<img src="x" onerror="alert(\'xss\')">',
            '"><script>alert("xss")</script>',
            '\';alert("xss");//'
        ];
        
        const vulnerableElements = [];
        
        // Test input fields
        const inputs = document.querySelectorAll('input[type="text"], textarea');
        inputs.forEach((input, index) => {
            testPayloads.forEach(payload => {
                input.value = payload;
                
                // Check if payload is reflected without sanitization
                if (input.value === payload) {
                    vulnerableElements.push({
                        element: `Input ${index}`,
                        payload,
                        type: 'REFLECTED_XSS'
                    });
                }
            });
        });
        
        // Test URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        urlParams.forEach((value, key) => {
            testPayloads.forEach(payload => {
                if (value.includes(payload)) {
                    vulnerableElements.push({
                        element: `URL parameter: ${key}`,
                        payload,
                        type: 'URL_XSS'
                    });
                }
            });
        });
        
        const status = vulnerableElements.length === 0 ? 'PASSED' : 'FAILED';
        
        if (vulnerableElements.length > 0) {
            this.vulnerabilities.push(...vulnerableElements.map(v => ({
                type: v.type,
                severity: 'HIGH',
                description: `XSS vulnerability in ${v.element}`,
                payload: v.payload
            })));
        }
        
        return {
            status,
            vulnerableElements: vulnerableElements.length,
            details: `XSS protection: ${vulnerableElements.length === 0 ? 'Secure ✓' : `${vulnerableElements.length} vulnerabilities found ✗`}`
        };
    }

    testCSRFProtection() {
        const forms = document.querySelectorAll('form');
        const missingCSRF = [];
        
        forms.forEach((form, index) => {
            const csrfToken = form.querySelector('input[name="csrfmiddlewaretoken"]') ||
                            form.querySelector('input[name="_token"]') ||
                            form.querySelector('meta[name="csrf-token"]');
            
            if (!csrfToken && form.method.toLowerCase() === 'post') {
                missingCSRF.push(`Form ${index}`);
            }
        });
        
        const status = missingCSRF.length === 0 ? 'PASSED' : 'FAILED';
        
        if (missingCSRF.length > 0) {
            this.vulnerabilities.push({
                type: 'CSRF_MISSING',
                severity: 'HIGH',
                description: `CSRF protection missing in ${missingCSRF.length} forms`
            });
        }
        
        return {
            status,
            totalForms: forms.length,
            missingCSRF: missingCSRF.length,
            details: `CSRF protection: ${missingCSRF.length === 0 ? 'All forms protected ✓' : `${missingCSRF.length} forms missing protection ✗`}`
        };
    }

    testInputSanitization() {
        const dangerousInputs = [
            '<script>',
            'javascript:',
            'onload=',
            'onerror=',
            'eval(',
            'document.cookie'
        ];
        
        const inputs = document.querySelectorAll('input, textarea');
        const unsanitizedInputs = [];
        
        inputs.forEach((input, index) => {
            dangerousInputs.forEach(dangerous => {
                input.value = dangerous;
                
                // Check if dangerous input is accepted without sanitization
                if (input.value.includes(dangerous)) {
                    unsanitizedInputs.push({
                        element: `Input ${index}`,
                        dangerous
                    });
                }
            });
        });
        
        const status = unsanitizedInputs.length === 0 ? 'PASSED' : 'FAILED';
        
        return {
            status,
            unsanitizedInputs: unsanitizedInputs.length,
            details: `Input sanitization: ${unsanitizedInputs.length === 0 ? 'Properly sanitized ✓' : `${unsanitizedInputs.length} inputs vulnerable ✗`}`
        };
    }

    testAuthSecurity() {
        const authIssues = [];
        
        // Check for password fields without proper attributes
        const passwordFields = document.querySelectorAll('input[type="password"]');
        passwordFields.forEach((field, index) => {
            if (!field.hasAttribute('autocomplete')) {
                authIssues.push(`Password field ${index} missing autocomplete attribute`);
            }
        });
        
        // Check for login forms without HTTPS (in production)
        const loginForms = document.querySelectorAll('form[action*="login"], form[action*="auth"]');
        if (location.protocol === 'http:' && location.hostname !== 'localhost') {
            loginForms.forEach((form, index) => {
                authIssues.push(`Login form ${index} not using HTTPS`);
            });
        }
        
        // Check for session storage of sensitive data
        const sensitiveKeys = ['password', 'token', 'secret', 'key'];
        sensitiveKeys.forEach(key => {
            if (localStorage.getItem(key) || sessionStorage.getItem(key)) {
                authIssues.push(`Sensitive data '${key}' stored in browser storage`);
            }
        });
        
        const status = authIssues.length === 0 ? 'PASSED' : 'FAILED';
        
        if (authIssues.length > 0) {
            this.vulnerabilities.push({
                type: 'AUTH_SECURITY',
                severity: 'MEDIUM',
                description: `Authentication security issues: ${authIssues.join(', ')}`
            });
        }
        
        return {
            status,
            issues: authIssues.length,
            details: `Authentication security: ${authIssues.length === 0 ? 'Secure ✓' : `${authIssues.length} issues found ✗`}`
        };
    }

    testCloudDomainSecurity() {
        const allowedDomains = [
            'cloudinary.com',
            'imagekit.io',
            'backblazeb2.com'
        ];
        
        const images = document.querySelectorAll('img');
        const scripts = document.querySelectorAll('script[src]');
        const links = document.querySelectorAll('link[href]');
        
        const unauthorizedDomains = [];
        
        // Check image sources
        images.forEach(img => {
            const src = img.src;
            if (src && src.startsWith('http')) {
                const domain = new URL(src).hostname;
                if (!allowedDomains.some(allowed => domain.includes(allowed)) && 
                    !domain.includes(location.hostname)) {
                    unauthorizedDomains.push(`Image: ${domain}`);
                }
            }
        });
        
        // Check script sources
        scripts.forEach(script => {
            const src = script.src;
            if (src && src.startsWith('http')) {
                const domain = new URL(src).hostname;
                const trustedCDNs = ['cdn.jsdelivr.net', 'cdnjs.cloudflare.com', 'unpkg.com'];
                if (!trustedCDNs.some(cdn => domain.includes(cdn)) && 
                    !domain.includes(location.hostname)) {
                    unauthorizedDomains.push(`Script: ${domain}`);
                }
            }
        });
        
        const status = unauthorizedDomains.length === 0 ? 'PASSED' : 'WARNING';
        
        return {
            status,
            unauthorizedDomains: unauthorizedDomains.length,
            allowedDomains,
            details: `Cloud domain security: ${unauthorizedDomains.length === 0 ? 'All domains authorized ✓' : `${unauthorizedDomains.length} unauthorized domains ⚠️`}`
        };
    }

    getCSPFromResponse() {
        // This would typically check response headers
        // For client-side testing, we simulate this
        return document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content || null;
    }

    generateSecurityReport() {
        const totalTests = Object.keys(this.results).length;
        const passedTests = Object.values(this.results).filter(r => r.status === 'PASSED').length;
        const failedTests = Object.values(this.results).filter(r => r.status === 'FAILED').length;
        const warningTests = Object.values(this.results).filter(r => r.status === 'WARNING').length;
        
        const criticalVulns = this.vulnerabilities.filter(v => v.severity === 'HIGH').length;
        const mediumVulns = this.vulnerabilities.filter(v => v.severity === 'MEDIUM').length;
        const lowVulns = this.vulnerabilities.filter(v => v.severity === 'LOW').length;
        
        const securityScore = Math.max(0, 100 - (criticalVulns * 30) - (mediumVulns * 15) - (lowVulns * 5));
        
        const report = {
            summary: {
                total: totalTests,
                passed: passedTests,
                failed: failedTests,
                warnings: warningTests,
                securityScore: Math.round(securityScore)
            },
            vulnerabilities: {
                critical: criticalVulns,
                medium: mediumVulns,
                low: lowVulns,
                total: this.vulnerabilities.length,
                details: this.vulnerabilities
            },
            results: this.results,
            timestamp: new Date().toISOString()
        };
        
        console.log('🔒 Security Test Report:', report);
        
        // Log security recommendations
        if (this.vulnerabilities.length > 0) {
            console.log('⚠️ Security Recommendations:');
            this.vulnerabilities.forEach(vuln => {
                console.log(`  - ${vuln.type}: ${vuln.description}`);
            });
        }
        
        return report;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SecurityTestSuite;
}