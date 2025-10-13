import { themes as prismThemes } from 'prism-react-renderer';
import type { Config } from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

const config: Config = {
	title: 'Search for projects',
	favicon: 'img/favicon.ico',
	future: {
		v4: true, // Improve compatibility with the upcoming Docusaurus v4
	},
	url: 'https://your-docusaurus-site.example.com',
	baseUrl: '/',
	organizationName: 'facebook', // Usually your GitHub org/user name.
	projectName: 'docusaurus', // Usually your repo name.
	onBrokenLinks: 'throw',
	onBrokenMarkdownLinks: 'warn',
	i18n: {
		defaultLocale: 'en',
		locales: ['en'],
	},
	presets: [
		[
			"@docusaurus/preset-classic",
			{
				docs: {
					routeBasePath: '/',
					sidebarCollapsed: true,
					sidebarPath: './sidebars.ts',
				},
				blog: false,
				theme: {
					customCss: [
						'./src/css/style.css',
						'./src/css/custom.scss'
					]
				},
			} satisfies Preset.Options,
		],
	],
	plugins: ['docusaurus-plugin-sass'],
	themeConfig: {
		colorMode: {
			defaultMode: 'dark',
			disableSwitch: false,
			respectPrefersColorScheme: false,
		},
		sidebar: {
			hideable: true,
			autoCollapseCategories: true
		},
		image: 'img/docusaurus-social-card.jpg',
		navbar: {
			title: 'Byper',
			logo: {
				alt: 'Byper Logo',
				src: 'img/logo.svg',
			},
			items: [
				{
					type: 'docSidebar',
					sidebarId: 'tutorialSidebar',
					position: 'left',
					label: 'Docs',
				}
			]
		},
		prism: {
			theme: prismThemes.vsDark,
			darkTheme: prismThemes.vsDark
		}

	} satisfies Preset.ThemeConfig,
};

export default config;