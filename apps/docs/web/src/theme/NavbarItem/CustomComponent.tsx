import { Dropdown, MenuProps } from 'antd';
import React, { useState } from 'react';

export default function CustomComponent(props: any) {
    const [search, setSearch] = useState<string>("");
    const [results, setResults] = useState<MenuProps['items']>([]);


    const onKeyDown = async (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === "Enter" && search.trim() !== "")
            window.location.href = `/search?pkg=${search}`;
    }

    return (
        <>
            <a
                href="/docs/intro"
                style={{
                    color: 'black',
                    textDecoration: 'none',
                    fontWeight: '700'
                }}
            >
                Docs
            </a>
            {/* <div className='search-in-nav'>
                <Dropdown menu={{ items: results }} open={results.length > 0} placement='bottom'>
                    <input onKeyDown={onKeyDown} placeholder='Search projects' onChange={(e) => setSearch(e.target.value.toLowerCase())} />
                </Dropdown>
            </div> */}
        </>
    );
}
