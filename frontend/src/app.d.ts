/// <reference types="@sveltejs/kit" />

declare module '*.svelte' {
	import { SvelteComponentTyped } from 'svelte';

	export default class Component<
		Props = {},
		Events = {},
		Slots = {}
	> extends SvelteComponentTyped<Props, Events, Slots> {}
}