import { useEffect, useState, type ReactNode } from 'react';

import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';

import ReactMarkdown from 'react-markdown';
import rehypeSanitize from 'rehype-sanitize';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';
import CodeBlock from "@theme/CodeBlock";
import { FaBeer, FaGithub, FaGlobe } from "react-icons/fa";


type PackageType = {
	name: string;
	description: string;
	version: string;
	releases: any[];
	summary: string;
	requires_python: string;
	license: string;
	yanked: boolean;
	repository: string;
	documentation: string;
	classifiers: string[];
	project_urls: any[];
	vulnerabilities: any[]
};

const Search: React.FC = (): ReactNode => {
	const { siteConfig } = useDocusaurusContext();
	const [pkg, setPkg] = useState<PackageType>();
	const [whoIsActive, setWhoIsActive] = useState<string>("description");
	const [search, setSearch] = useState<string>("");


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
			const { name, version, yanked, description, license, summary, requires_python, project_urls, classifiers } = data.info
			const { releases: releases_raw, vulnerabilities, } = data

			// for (const key in url) {
			// 	if (url[key].toLowerCase().includes("github.com") && site == "github") {
			// 		window.open(url[key], "_blank");
			// 	} else if (key.toLowerCase().includes("documentation") && site == "documentation") {
			// 		window.open(url[key]);
			// 	}
			// }

			const releases = []
			let repository = null
			let documentation = null
			for (const key in releases_raw) {
				for (const key in project_urls) {
					if (project_urls[key].includes("github.com"))
						repository = project_urls[key]

					if (key.toLowerCase().includes("documentation"))
						documentation = project_urls[key]
				}

				releases.push(Object.assign(releases_raw[key][0], {
					version: key
				}))
			}

			// console.log(releases.length);
			const pksData = {
				name,
				version,
				yanked,
				license,
				classifiers,
				releases: releases,
				summary,
				requires_python,
				project_urls,
				description,
				vulnerabilities,
				repository,
				documentation
			}
			console.log({ pksData });

			setPkg(pksData);

		}).catch((err) => console.log({ err }));


	}, []);

	const MarkDown: React.FC = () => {
		const onClickUrls = (url: any[], site: string) => {
			for (const key in url) {
				if (url[key].toLowerCase().includes("github.com") && site == "github") {
					window.open(url[key], "_blank");
				} else if (key.toLowerCase().includes("documentation") && site == "documentation") {
					window.open(url[key]);
				}
			}
		}
		return (
			<section className="markdown">
				<div className="description">
					<ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw, rehypeSanitize]}>
						{pkg?.description}
					</ReactMarkdown>
				</div>
				<div className="info">
					<div className="urls">
						{pkg?.documentation ? <div onClick={() => onClickUrls(pkg?.project_urls, "documentation")} className="icon">
							<FaGlobe />
						</div> : null}
						{pkg?.repository ? <div onClick={() => onClickUrls(pkg?.project_urls, "github")} className="icon">
							<FaGithub color='black' />
						</div> : null}
					</div>
					<CodeBlock>byper add {pkg?.name}=={pkg?.version}</CodeBlock>
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
						<CodeBlock className='code-block'>byper add {pkg.name}=={release?.version}</CodeBlock>
						<p><b>Requires Python:</b> {pkg.requires_python}</p>
						<p><b>Size:</b> {bytesToMB(release?.size)} mb</p>
						<p><b>Yanked:</b> {pkg.yanked ? "Yes" : "No"}</p>
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
							<input onKeyDown={onKeyDown} onChange={(e) => setSearch(e.target.value.toUpperCase())} type="text" placeholder='Search...' />
							<button onClick={onSearch} is-active={String(whoIsActive === "releases")} id="releases">Releases</button>
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