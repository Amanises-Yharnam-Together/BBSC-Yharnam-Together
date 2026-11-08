// SPDX-FileCopyrightText: Copyright 2024 shadPS4 Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#pragma once

#include <cstdlib>

#include "common/small_vector.h"
#include "common/types.h"
#include "shader_recompiler/info.h"

namespace Serialization {
struct Archive;
}

namespace Shader::Gcn {

struct VertexAttribute {
    enum InstanceIdType : u8 {
        None = 0,
        OverStepRate0 = 1,
        OverStepRate1 = 2,
        Plain = 3,
    };

    u8 dest_vgpr;     ///< Destination VGPR to load first component.
    u8 num_elements;  ///< Number of components to load
    u8 sgpr_base;     ///< SGPR that contains the pointer to the list of vertex V#
    u8 dword_offset;  ///< The dword offset of the V# that describes this attribute.
    u8 instance_data; ///< Indicates that the buffer will be accessed in instance rate
    u8 inst_offset;   ///< Instruction offset applied on the formatted buffer loads
    u8 data_format;   ///< Data format override when typed buffer loads are used
    u8 num_format;    ///< Number format override when typed buffer loads are used

    InstanceIdType GetStepRate() const {
        return static_cast<InstanceIdType>(instance_data);
    }

    constexpr AmdGpu::Buffer GetSharp(const Shader::Info& info) const noexcept {
        auto buffer = info.ReadUdReg<AmdGpu::Buffer>(sgpr_base, dword_offset);
        buffer.base_address += inst_offset;
        if (data_format) {
            buffer.data_format = data_format;
            buffer.num_format = num_format;
        }
        return buffer;
    }

    bool operator==(const VertexAttribute& other) const = default;
};

struct FetchShaderData {
    u32 size = 0;
    SmallVector<VertexAttribute, 8> attributes;
    s8 vertex_offset_sgpr = -1;   ///< SGPR of vertex offset from VADDR
    s8 instance_offset_sgpr = -1; ///< SGPR of instance offset from VADDR

    bool operator==(const FetchShaderData& other) const {
        return attributes == other.attributes && vertex_offset_sgpr == other.vertex_offset_sgpr &&
               instance_offset_sgpr == other.instance_offset_sgpr;
    }

    bool Empty() const {
        return size == 0;
    }

    void Serialize(Serialization::Archive& ar) const;
    bool Deserialize(Serialization::Archive& buffer);
};

const u32* GetFetchShaderCode(const Info& info, u32 sgpr_base);

bool ParseFetchShader(const Shader::Info& info, FetchShaderData& out_fetch_data);

/// bbport: a V# without records fetches zeros through a float input. Described to Vulkan from
/// its own fields, a zeroed V# is a VK_FORMAT_UNDEFINED vertex attribute; an NVIDIA driver lost
/// the device ("WriteInvalid at 0x0") on the first submit after a draw with one. The
/// specialization keeps none of such a V#'s fields (number class Float, swizzle zero), so the
/// shader declares a float input and writes zeros to its registers. BB_NULL_VERTEX_INPUT=0
/// describes the V#'s own format, stride and swizzle as before.
inline bool NullVertexInputEnabled() noexcept {
    static const bool enabled = [] {
        const char* value = std::getenv("BB_NULL_VERTEX_INPUT");
        return !value || value[0] != '0';
    }();
    return enabled;
}

inline bool IsNullVertexInput(const AmdGpu::Buffer& sharp, bool enabled) noexcept {
    return enabled && !sharp;
}

inline bool IsNullVertexInput(const AmdGpu::Buffer& sharp) noexcept {
    return IsNullVertexInput(sharp, NullVertexInputEnabled());
}

struct VertexInputFormat {
    AmdGpu::DataFormat data_format;
    AmdGpu::NumberFormat num_format;
    u32 stride;
};

/// The host vertex input of an attribute: a null one fetches a float4 from no buffer.
inline VertexInputFormat GetVertexInputFormat(const AmdGpu::Buffer& sharp, bool null) noexcept {
    if (null) {
        return {AmdGpu::DataFormat::Format32_32_32_32, AmdGpu::NumberFormat::Float, 0};
    }
    return {sharp.GetDataFmt(), sharp.GetNumberFmt(), sharp.GetStride()};
}

inline VertexInputFormat GetVertexInputFormat(const AmdGpu::Buffer& sharp) noexcept {
    return GetVertexInputFormat(sharp, IsNullVertexInput(sharp));
}

} // namespace Shader::Gcn
