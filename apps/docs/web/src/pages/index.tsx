import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import HomePage from '../components/Home';



const HomeScreen: React.FC = () => {
	const { siteConfig } = useDocusaurusContext();

	return (
		<Layout title={`Hello from ${siteConfig.title}`} >
			<main>
				<HomePage />
			</main>
		</Layout>
	);
}

export default HomeScreen;