// frontend/src/routes/page.svelte.spec.ts
import { page } from '@vitest/browser/context';
import { describe, it, expect } from 'vitest';
import { render } from 'vitest-browser-svelte';
import Page from './+page.svelte';

describe('+page.svelte', () => {
    it('renders header h1', async () => {
        const { getByRole } = render(Page);
        
        const heading = getByRole('heading', { level: 1, name: /HalluDetector/i });
        
        expect(heading).toBeTruthy();
    });
});