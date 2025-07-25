import { useEffect, useState, type ReactNode } from 'react';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import pandasLogo from '@site/static/img/pandas.png'
import pyTorchLogo from '@site/static/img/pyTorch.png'
import axios from 'axios';
import { MenuProps } from 'antd';
import HomePage from '../components/Home';


type FeatureItem = {
	title: string;
	logo: string;
	description: ReactNode;
};

const features: FeatureItem[] = [
	{
		title: 'Pandas',
		logo: pandasLogo,
		description: (
			<p>
				A Python package that provides fast, flexible, and expressive data structures designed to make working with "relational" or "labeled" data both easy and intuitive.
			</p>
		),
	},
	{
		title: 'Pandas',
		logo: pandasLogo,
		description: (
			<p>
				A Python package that provides fast, flexible, and expressive data structures designed to make working with "relational" or "labeled" data both easy and intuitive.
			</p>
		),
	},
	{
		title: 'Matplotlib',
		logo: pandasLogo,
		description: (
			<>
				Matplotlib is the core plotting library in Python, enabling you to generate static, animated, and interactive visualizations with ease.
			</>
		),
	},
	{
		title: 'NumPy',
		logo: pandasLogo,
		description: (
			<>
				NumPy is the foundation of scientific computing in Python. Its fast array operations power everything from machine learning to finance.
			</>
		),
	},
	{
		title: 'PyTorch',
		logo: pyTorchLogo,
		description: (
			<p>
				PyTorch is a flexible deep learning framework that helps researchers and developers build, train, and deploy powerful AI models with ease.
			</p>
		),
	},
	{
		title: 'Powered by React',
		logo: pandasLogo,
		description: (
			<>
				Extend or customize your website layout by reusing React. Docusaurus can
				be extended while reusing the same header and footer.
			</>
		),
	},
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
			await axios.get(`http://localhost:3001/search?pkg=${value.toLowerCase()}`).then(({ data }) => {
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
	}, [value]);

	return (
		<Layout title={`Hello from ${siteConfig.title}`} >
			<main>
				<HomePage />
			</main>
		</Layout>
	);
}

export default HomeScreen;