import { useEffect, useState, type ReactNode } from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Heading from '@theme/Heading';
import Input from '../Inputs';
import pandasLogo from '@site/static/img/pandas.png'
import pyTorchLogo from '@site/static/img/pyTorch.png'
import axios from 'axios';
import { MenuProps } from 'antd';
import { FaDownload } from 'react-icons/fa';
import { MdOutlineDownload, MdOutlineDownloading, MdOutlineTimer, MdTimer } from 'react-icons/md';
import moment from 'moment';
import "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"

type FeatureItem = {
	title: string;
	href: string;
	dependencies: string[];
};

const features: FeatureItem[] = [
	{
		title: 'pandas',
		href: '/search?pkg=pandas',
		dependencies: [
			"test",
			"pyarrow",
			"performance",
			"and 19 more..."
		],
	},
	{
		title: 'matplotlib',
		href: '/search?pkg=matplotlib',
		dependencies: [
			"dev"
		],
	},
	{
		title: 'numpy',
		href: '/search?pkg=numpy',
		dependencies: [],
	},
	{
		title: 'torch',
		href: '/search?pkg=torch',
		dependencies: [
			"optree",
			"opt-einsum"
		],
	}
];

const HomeScreen: React.FC = () => {
	const { siteConfig } = useDocusaurusContext();
	const [value, setValue] = useState('');
	const [results, setResults] = useState<MenuProps['items']>([]);


	const onKeyDown = async (e: React.KeyboardEvent<HTMLInputElement>) => {
		console.log({ value });

		if (e.key === "Enter" && value.trim() !== "")
			window.location.href = `/search?pkg=${value.toLowerCase()}`;
	}

	useEffect(() => {
		if (!value) return;

		const delay = setTimeout(async () => {
			await axios.get(`http://localhost:3001/api/project/search?pkg=${value.toLowerCase()}`).then(({ data }) => {
				if (Array.isArray(data))
					setResults(data?.map((item: any, key) => {
						return {
							key: key.toString(),
							label: (
								<a className='project-link' rel="noopener noreferrer" href={`/search?pkg=${item.project}`}>
									{item.project}
								</a>
							),
						}
					}))
				else
					setResults([]);

				console.log(data);

			}).catch(err => {
				console.error(err)
			});
		}, 300);

		return () => clearTimeout(delay);
	}, [value]);

	const onSearch = async () => {
		if (!value) return

		window.location.href = `/search?pkg=${value.toLowerCase()}`

	}

	return (
		<div className="Home ">
			<header className={clsx('hero--primary')}>
				<div className="container">
					<div className='search'>
						<Input onKeyDown={onKeyDown} items={results} placeholder='Search projects' onChange={(e) => setValue(e.target.value.toLowerCase())} />
						<button onClick={onSearch} id="releases">Search</button>
					</div>
					<h1 className="text-xl text-center title">
						{/* byper is a environment manager for <span>Python</span> */}
						Start strong. Start fast. Stay organized. Build anything with Byper.
					</h1>
					<p className="text-xl sub-title text-muted-foreground max-w-[600px] mx-auto">
						Ready to build? Let byper manage your environment so you can focus on what matters.
					</p>
					<p className="hero__subtitle">{siteConfig.tagline}</p>
					<Link className="button button--secondary button--lg" to="/docs/intro">
						Getting Started
					</Link>
				</div>
			</header>
			{/* <section className="Features custom-grid">
				<div className="container">
					<div className="sub-section">
						<h1>Popular projects</h1>
						<span>Some of the most downloaded packages on PyPI</span>
					</div>
				</div>
				<div className="container">
					{features.map((feature, idx) => (
						<a href={feature.href} key={idx} className="feature">
							<div className='header'>
								<b>{feature.title}</b>
								<span>0.0.1</span>
							</div>
							<p>Fundamental package for array computing in Python</p>

							<div className="dependencies">
								<div className="box">
									{feature?.dependencies?.map((dep: string) => (
										<span>{dep}</span>
									))}

								</div>
							</div>
							<div className="stats">
								<div className="stat">
									<MdOutlineDownload />
									<span>100M/Weekly</span>
								</div>
								<>
									<MdOutlineTimer />
									<span>{moment("2025-01-01").fromNow()}</span>
								</>
							</div>
						</a>
					))}
				</div>
			</section> */}
			<section className="py-16 bg-white">
				<div className="container mx-auto px-4">
					<div className="mb-12 text-center">
						<h2 className="text-2xl md:text-3xl font-bold">Popular Projects</h2>
						<p className="text-muted-foreground mt-2">Some of the most downloaded packages on PyPI</p>
					</div>

					<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
						{features.map((feature, idx) => (
							<a
								href={feature.href}
								key={idx}
								className="border border-gray-200 rounded-lg p-6 shadow-sm hover:shadow-md transition"
							>
								<div className="flex justify-between items-center mb-2">
									<b className="text-lg font-semibold">{feature.title}</b>
									<span className="text-sm text-gray-500">0.0.1</span>
								</div>

								<p className="text-sm text-gray-700 mb-4">
									Fundamental package for array computing in Python
								</p>

								{feature.dependencies?.length > 0 && (
									<div className="flex flex-wrap gap-2 mb-4">
										{feature.dependencies.map((dep: string) => (
											<span
												key={dep}
												className="text-xs bg-gray-100 px-2 py-1 rounded-full text-gray-700"
											>
												{dep}
											</span>
										))}
									</div>
								)}

								<div className="flex items-center justify-between text-sm text-gray-500 mt-auto">
									<div className="flex items-center gap-1">
										<MdOutlineDownload className="text-lg" />
										<span>100M/Weekly</span>
									</div>
									<div className="flex items-center gap-1">
										<MdOutlineTimer className="text-lg" />
										<span>{moment("2025-01-01").fromNow()}</span>
									</div>
								</div>
							</a>
						))}
					</div>
				</div>
			</section>
		</div>



	);
}

export default HomeScreen;