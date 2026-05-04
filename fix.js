const fs = require('fs');
const path = require('path');

const dir = path.join(__dirname, 'ui', 'react-app', 'public', 'src', 'pages');

const filesToFix = fs.readdirSync(dir).filter(f => f.endsWith('.tsx'));

for (const file of filesToFix) {
    const p = path.join(dir, file);
    let content = fs.readFileSync(p, 'utf8');

    // Remove `<Grid item` -> `<Grid`
    content = content.replace(/<Grid\s+item/g, '<Grid');
    
    // Remove `item\n` or `item ` if it's inside a Grid tag. A safe way is to regex:
    // This handles `<Grid ... item ...>` but doing `<Grid item` handles 99%. Let's see if `item ` alone is safe.
    content = content.replace(/<Grid\b([^>]*)item\b/g, '<Grid$1');

    // DeepfakeTab.tsx: Database -> Dataset
    if (file === 'DeepfakeTab.tsx') {
        content = content.replace(/Database/g, 'Dataset');
        // also explicit anys
        content = content.replace(/severity\)/g, 'severity: any)');
    }

    // AdminPanel.tsx: Brain -> Memory
    if (file === 'AdminPanel.tsx') {
        content = content.replace(/Brain/g, 'Memory');
        content = content.replace(/policyId,/g, 'policyId: any,');
        content = content.replace(/enabled\)/g, 'enabled: any)');
        content = content.replace(/event,/g, 'event: any,');
        content = content.replace(/newValue\)/g, 'newValue: any)');
        content = content.replace(/adjustments/g, 'adjustments: any');
        content = content.replace(/data\)/g, 'data: any)');
        content = content.replace(/results,/g, 'results: any,');
        content = content.replace(/alert,/g, 'alert: any,');
        content = content.replace(/action\)/g, 'action: any)');
    }

    // Dashboard.tsx: requiredPermissions -> requiredPermission
    if (file === 'Dashboard.tsx') {
        content = content.replace(/requiredPermissions/g, 'requiredPermission');
        content = content.replace(/a\)/g, 'a: any)');
        content = content.replace(/i\)/g, 'i: any)');
        content = content.replace(/newPage\)/g, 'newPage: any)');
        content = content.replace(/onFilterChange=\{(.*?)\}/g, 'onFilterChange={$1} orgId="default"');
        content = content.replace(/activeTab,/g, 'activeTab: any,');
        content = content.replace(/setActiveTab\}/g, 'setActiveTab: any}');
        content = content.replace(/tier\)/g, 'tier: any)');
    }

    // DashboardHome.tsx
    if (file === 'DashboardHome.tsx') {
        content = content.replace(/score\)/g, 'score: any)');
        content = content.replace(/onEnrichmentComplete/g, 'personId="default" onEnrichmentComplete');
    }

    // BiasReportTab.tsx
    if (file === 'BiasReportTab.tsx') {
        content = content.replace(/event,/g, 'event: any,');
        content = content.replace(/newPage\)/g, 'newPage: any)');
        content = content.replace(/g\)/g, 'g: any)');
        content = content.replace(/group,/g, 'group: any,');
        content = content.replace(/idx\)/g, 'idx: any)');
    }

    // Enroll.tsx
    if (file === 'Enroll.tsx') {
        content = content.replace(/useState\(\[\]\)/g, 'useState<any[]>([])');
        content = content.replace(/useState\(null\)/g, 'useState<any>(null)');
        content = content.replace(/e\)/g, 'e: any)');
        content = content.replace(/index\)/g, 'index: any)');
    }

    fs.writeFileSync(p, content, 'utf8');
}

console.log("Fixes applied.");
