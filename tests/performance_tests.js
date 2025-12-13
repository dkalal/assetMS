/**
 * Performance Testing Suite
 * Tests system performance, load handling, and optimization
 */

class PerformanceTestSuite {
    constructor() {
        this.results = {};
        this.benchmarks = {
            pageLoad: 2000,      // 2 seconds max
            apiResponse: 1000,   // 1 second max
            imageLoad: 3000,     // 3 seconds max
            qrScan: 5000        // 5 seconds max
        };
    }

    async runAllTests() {
        console.log('🚀 Starting Performance Tests');
        
        const tests = [
            { name: 'Page Load Performance', test: () => this.testPageLoad() },
            { name: 'API Response Time', test: () => this.testApiResponse() },
            { name: 'Image Loading Speed', test: () => this.testImageLoading() },
            { name: 'QR Scanner Performance', test: () => this.testQRScannerPerformance() },
            { name: 'Memory Usage', test: () => this.testMemoryUsage() },
            { name: 'Concurrent Operations', test: () => this.testConcurrentOperations() }
        ];

        for (const test of tests) {
            try {
                const result = await test.test();
                this.results[test.name] = result;
                console.log(`✅ ${test.name}: ${result.status}`);
            } catch (error) {
                this.results[test.name] = { status: 'FAILED', error: error.message };
                console.log(`❌ ${test.name}: FAILED - ${error.message}`);
            }
        }

        return this.generateReport();
    }

    async testPageLoad() {
        const startTime = performance.now();
        
        return new Promise((resolve) => {
            window.addEventListener('load', () => {
                const loadTime = performance.now() - startTime;
                const status = loadTime < this.benchmarks.pageLoad ? 'PASSED' : 'FAILED';
                
                resolve({
                    status,
                    loadTime: Math.round(loadTime),
                    benchmark: this.benchmarks.pageLoad,
                    details: `Page loaded in ${Math.round(loadTime)}ms`
                });
            });
        });
    }

    async testApiResponse() {
        const endpoints = ['/api/assets/', '/api/users/', '/api/health/'];
        const results = [];

        for (const endpoint of endpoints) {
            const startTime = performance.now();
            
            try {
                const response = await fetch(endpoint);
                const responseTime = performance.now() - startTime;
                
                results.push({
                    endpoint,
                    responseTime: Math.round(responseTime),
                    status: response.status,
                    passed: responseTime < this.benchmarks.apiResponse
                });
            } catch (error) {
                results.push({
                    endpoint,
                    responseTime: null,
                    status: 'ERROR',
                    error: error.message,
                    passed: false
                });
            }
        }

        const allPassed = results.every(r => r.passed);
        const avgResponseTime = results
            .filter(r => r.responseTime)
            .reduce((sum, r) => sum + r.responseTime, 0) / results.length;

        return {
            status: allPassed ? 'PASSED' : 'FAILED',
            averageResponseTime: Math.round(avgResponseTime),
            benchmark: this.benchmarks.apiResponse,
            details: results
        };
    }

    async testImageLoading() {
        const testImages = [
            'https://via.placeholder.com/300x300.jpg',
            'https://via.placeholder.com/600x400.jpg',
            'https://via.placeholder.com/1200x800.jpg'
        ];

        const results = [];

        for (const imageUrl of testImages) {
            const startTime = performance.now();
            
            try {
                await new Promise((resolve, reject) => {
                    const img = new Image();
                    img.onload = () => {
                        const loadTime = performance.now() - startTime;
                        results.push({
                            url: imageUrl,
                            loadTime: Math.round(loadTime),
                            passed: loadTime < this.benchmarks.imageLoad
                        });
                        resolve();
                    };
                    img.onerror = reject;
                    img.src = imageUrl;
                });
            } catch (error) {
                results.push({
                    url: imageUrl,
                    loadTime: null,
                    error: error.message,
                    passed: false
                });
            }
        }

        const allPassed = results.every(r => r.passed);
        const avgLoadTime = results
            .filter(r => r.loadTime)
            .reduce((sum, r) => sum + r.loadTime, 0) / results.length;

        return {
            status: allPassed ? 'PASSED' : 'FAILED',
            averageLoadTime: Math.round(avgLoadTime),
            benchmark: this.benchmarks.imageLoad,
            details: results
        };
    }

    async testQRScannerPerformance() {
        const startTime = performance.now();
        
        try {
            // Test QR scanner initialization time
            if (typeof Html5Qrcode !== 'undefined') {
                const cameras = await Html5Qrcode.getCameras();
                const initTime = performance.now() - startTime;
                
                return {
                    status: initTime < this.benchmarks.qrScan ? 'PASSED' : 'FAILED',
                    initTime: Math.round(initTime),
                    camerasFound: cameras.length,
                    benchmark: this.benchmarks.qrScan,
                    details: `QR scanner initialized in ${Math.round(initTime)}ms with ${cameras.length} cameras`
                };
            } else {
                return {
                    status: 'FAILED',
                    error: 'Html5Qrcode library not available',
                    details: 'QR scanner library not loaded'
                };
            }
        } catch (error) {
            return {
                status: 'FAILED',
                error: error.message,
                details: 'QR scanner performance test failed'
            };
        }
    }

    async testMemoryUsage() {
        if (performance.memory) {
            const memory = performance.memory;
            const usedMB = Math.round(memory.usedJSHeapSize / 1024 / 1024);
            const totalMB = Math.round(memory.totalJSHeapSize / 1024 / 1024);
            const limitMB = Math.round(memory.jsHeapSizeLimit / 1024 / 1024);
            
            const memoryUsagePercent = (usedMB / limitMB) * 100;
            const status = memoryUsagePercent < 80 ? 'PASSED' : 'FAILED';
            
            return {
                status,
                usedMemory: usedMB,
                totalMemory: totalMB,
                memoryLimit: limitMB,
                usagePercent: Math.round(memoryUsagePercent),
                details: `Memory usage: ${usedMB}MB / ${limitMB}MB (${Math.round(memoryUsagePercent)}%)`
            };
        } else {
            return {
                status: 'SKIPPED',
                details: 'Memory API not available in this browser'
            };
        }
    }

    async testConcurrentOperations() {
        const concurrentTasks = 10;
        const tasks = [];
        
        const startTime = performance.now();
        
        // Create concurrent fetch operations
        for (let i = 0; i < concurrentTasks; i++) {
            tasks.push(
                fetch('https://jsonplaceholder.typicode.com/posts/1')
                    .then(response => response.json())
                    .catch(error => ({ error: error.message }))
            );
        }
        
        try {
            const results = await Promise.all(tasks);
            const totalTime = performance.now() - startTime;
            
            const successCount = results.filter(r => !r.error).length;
            const successRate = (successCount / concurrentTasks) * 100;
            
            return {
                status: successRate >= 80 ? 'PASSED' : 'FAILED',
                totalTime: Math.round(totalTime),
                concurrentTasks,
                successCount,
                successRate: Math.round(successRate),
                details: `${successCount}/${concurrentTasks} concurrent operations succeeded in ${Math.round(totalTime)}ms`
            };
        } catch (error) {
            return {
                status: 'FAILED',
                error: error.message,
                details: 'Concurrent operations test failed'
            };
        }
    }

    generateReport() {
        const totalTests = Object.keys(this.results).length;
        const passedTests = Object.values(this.results).filter(r => r.status === 'PASSED').length;
        const failedTests = Object.values(this.results).filter(r => r.status === 'FAILED').length;
        const skippedTests = Object.values(this.results).filter(r => r.status === 'SKIPPED').length;
        
        const report = {
            summary: {
                total: totalTests,
                passed: passedTests,
                failed: failedTests,
                skipped: skippedTests,
                successRate: Math.round((passedTests / (totalTests - skippedTests)) * 100)
            },
            results: this.results,
            benchmarks: this.benchmarks,
            timestamp: new Date().toISOString()
        };
        
        console.log('📊 Performance Test Report:', report);
        return report;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PerformanceTestSuite;
}