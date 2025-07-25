import { Dropdown, MenuProps } from 'antd'
import React from 'react'
import { MdSearch,  } from 'react-icons/md'

type Props = {
    placeholder?: string
    onChange?: (event: React.ChangeEvent<HTMLInputElement>) => void
    onKeyDown?: (event: React.KeyboardEvent<HTMLInputElement>) => void
    items?: MenuProps['items']
}

const Input: React.FC<Props> = ({ placeholder = 'Search...', items = [], onKeyDown = (_) => { }, onChange = (_) => { } }: Props) => {

    const _onChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        onChange(event)
    }

    const _onKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
        onKeyDown(event)
    }


    return (
        <Dropdown menu={{ items }} open={items.length > 0} placement='bottom' >
            <div className="Input">
                <MdSearch />
                <input type="text" onKeyDown={_onKeyDown} onChange={_onChange} placeholder={placeholder} />
            </div>
        </Dropdown>
    )
}

export default Input
