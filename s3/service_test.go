// Licensed to the Apache Software Foundation (ASF) under one
// or more contributor license agreements.  See the NOTICE file
// distributed with this work for additional information
// regarding copyright ownership.  The ASF licenses this file
// to you under the Apache License, Version 2.0 (the
// "License"); you may not use this file except in compliance
// with the License.  You may obtain a copy of the License at
//
//   http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing,
// software distributed under the License is distributed on an
// "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
// KIND, either express or implied.  See the License for the
// specific language governing permissions and limitations
// under the License.

// generated by github.com/apache/opendal-go-services

package s3_test

import (
	"os"
	"testing"

	"github.com/stretchr/testify/require"
	"github.com/apache/opendal-go-services/s3"
)

func TestScheme(t *testing.T) {
	t.Parallel()
	assert := require.New(t)

	assert.Nil(s3.Scheme.LoadOnce())
	path := s3.Scheme.Path()
	assert.NotEmpty(path)
	assert.Nil(os.Remove(path))
}

