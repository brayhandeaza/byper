import { useEffect, useState, type ReactNode } from 'react';

import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';

import ReactMarkdown from 'react-markdown';
import rehypeSanitize from 'rehype-sanitize';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';
import CodeBlock from "@theme/CodeBlock";
import Tag from "@theme/Tag";
import TagsListInline from "@theme/TagsListInline";
import { FaBeer, FaDownload, FaGithub, FaGlobe } from "react-icons/fa";
import moment from 'moment';
import Input from '../components/Inputs';
import { Dropdown, MenuProps } from 'antd';
import axios from 'axios';


type PackageType = {
	name: string;
	description: string;
	version: string;
	releases: any[];
	release: any;
	summary: string;
	requires_python: string;
	license: string;
	yanked: boolean;
	repository: string;
	documentation: string;
	classifiers: string[];
	project_urls: any[];
	vulnerabilities: any[]
	dependencies: string[]
};

const Search: React.FC = (): ReactNode => {
	const { siteConfig } = useDocusaurusContext();
	const [pkg, setPkg] = useState<PackageType>();
	const [whoIsActive, setWhoIsActive] = useState<string>("description");
	const [search, setSearch] = useState<string>("");
	const [results, setResults] = useState<MenuProps['items']>([]);

	useEffect(() => {
		if (!search) return;

		const delay = setTimeout(async () => {
			await axios.get(`http://localhost:3001/api/project/search?pkg=${search.toLowerCase()}`).then(({ data }) => {
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

		return () => clearTimeout(delay); // Cleanup debounce
	}, [search]);


	useEffect(() => {
		const params = new URLSearchParams(window.location.search);
		const pkg = params.get("pkg"); // Replace 'your_key' with your actual key
		const version = params.get("v"); // Replace 'your_key' with your actual key

		if (!pkg) {
			window.location.href = "/404";
			return
		}

		fetch(`https://pypi.org/pypi/${pkg}/${version ? version + "/" : ""}json`).then(async (response) => {
			if (!response.ok) {
				window.location.href = "/404";
				return
			}

			const data = await response.json();
			const { name, version, provides_extra, yanked, description, license, summary, requires_python, project_urls, classifiers } = data.info
			const { releases: releases_raw, vulnerabilities, } = data
			console.log({ provides_extra });

			const releasesSorted = Object.entries(releases_raw).sort(([a], [b]) => {
				const [aMajor, aMinor, aPatch] = a.split('.').map(num => parseInt(num, 10));
				const [bMajor, bMinor, bPatch] = b.split('.').map(num => parseInt(num, 10))

				return (
					bMajor - aMajor ||
					bMinor - aMinor ||
					bPatch - aPatch
				);
			}).map(([key, value]) => {
				console.log({ key, value });
				return Object.assign(value[0] || {}, {
					version: key
				})
			})


			console.log({ data });


			let repository = null
			let documentation = null

			for (const key in project_urls) {
				if (project_urls[key].includes("github.com"))
					repository = project_urls[key]

				if (key.toLowerCase().includes("documentation"))
					documentation = project_urls[key]
			}

			console.log(data);
			const pksData = {
				name,
				version,
				yanked,
				license,
				classifiers,
				releases: releasesSorted,
				release: releasesSorted[0],
				summary,
				requires_python,
				project_urls,
				description,
				vulnerabilities,
				repository,
				documentation,
				dependencies: provides_extra
			}
			console.log({ pksData });

			setPkg(pksData);

		}).catch((err) => console.log({ err }));


	}, []);

	const MarkDown: React.FC = () => {
		return (
			<section className="markdown ">
				<div className="description">
					<ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw, rehypeSanitize]}>
						{pkg?.description}
					</ReactMarkdown>
				</div>
				<div className="info">
					<CodeBlock className='byper-copy' >byper add {pkg?.name}</CodeBlock>

					<b>Published: </b>
					<span>{moment(pkg?.release?.upload_time).fromNow()}</span><br />

					<b>Version: </b>
					<span>{pkg?.release?.version}</span>

					<div className="dependencies">
						<b>Dependencies:</b><br />
						<div className="box">
							{pkg?.dependencies?.map((dep: string) => (
								<span key={dep}>{dep}</span>
							))}
						</div>
					</div>
					<hr />
					<div onClick={() => window.open(pkg?.release?.url, "_blank")} className="download">
						<FaDownload />
						<span>Download .{pkg?.release.filename.split(".").pop()} file</span>
					</div>
				</div>

			</section>
		);
	}
	const Releases: React.FC = () => {
		const bytesToMB = (bytes: number) => {
			return (bytes / (1024 * 1024)).toFixed(2);
		}
		return (
			<div className='releases'>
				{pkg?.releases?.map((release: any) => (
					<div key={`${pkg.name}==${release?.version}`} className="release">
						<CodeBlock  className='code-block'>byper add {pkg.name}=={release?.version}</CodeBlock>
						<p><b>Python:</b> {pkg.requires_python}</p>
						<p><b>Size:</b> {bytesToMB(release?.size)} mb</p>
						<p><b>Yanked:</b> {pkg.yanked ? "Yes" : "No"}</p>

						<div onClick={() => window.open(pkg?.release?.url, "_blank")} className="download">
							<FaDownload />
							<span>Download .{pkg?.release.filename.split(".").pop()} file</span>
						</div>
					</div>
				))}
			</div>
		
		);
	}

	const RenderSessions: React.FC<{ name: string }> = ({ name }: { name: string }) => {
		switch (name) {
			case "releases":
				return <Releases />;
			default:
				return <MarkDown />
		}

	}

	const onSearch = async () => {
		if (!search) return

		window.location.href = `/search?pkg=${search.toLowerCase()}`

	}

	const onKeyDown = async (e: React.KeyboardEvent<HTMLInputElement>) => {
		if (e.key === "Enter" && search.trim() !== "")
			window.location.href = `/search?pkg=${search}`;
	}

	return (
		<div className="Search">
			<Layout>
				<main className="container">
					<menu>
						<div className='search'>
							<Input onKeyDown={onKeyDown} items={results} placeholder='Search projects' onChange={(e) => setSearch(e.target.value.toLowerCase())} />
							<button onClick={onSearch} is-active={String(whoIsActive === "releases")} id="releases">Search</button>
						</div>
						<div className="tabs">
							<button onClick={(e) => setWhoIsActive(e.currentTarget.id)} is-active={String(whoIsActive === "description")} id="description">Description</button>
							<button onClick={(e) => setWhoIsActive(e.currentTarget.id)} is-active={String(whoIsActive === "releases")} id="releases">Releases</button>
						</div>
					</menu>
					<section>
						<RenderSessions name={whoIsActive} />
					</section>
				</main>
			</Layout>
		</div>

	);
}


export default Search